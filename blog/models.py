import base64
from django.conf import settings
from django.core.mail import send_mail
from django.db import models
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (Mail, Attachment, FileContent, FileName, FileType, Disposition)

class Post(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    slug = models.SlugField(null=True, blank=True)
    youtube_video = models.TextField(default='', null=True, blank=True, help_text='This is for a single '\
                    'YouTube video to be displayed at the top of a post. '\
                    'To get the code, go to the video on YouTube, click on the "Share" option, and then '\
                    'click on "Embed". Copy and paste the code here. If you want the video to look good '\
                    'on phones, change the number in quotes for "width" from "560" to "75%" (It is at '\
                    'the very beginning of the code you posted).')
    text = models.TextField()
    created_date = models.DateTimeField(default=timezone.now)
    published_date = models.DateTimeField(blank=True, null=True)

    def publish(self):
        self.published_date = timezone.now()
        self.save()

    def approved_comments(self):
        return self.comments.filter(approved_comment=True)

    def save(self, *args, **kwargs):
        slug = slugify(self.title)
        self.slug = slug
        super(Post, self).save(*args, **kwargs)

    def __str__(self):
        return self.title

    def send(self, request):
        subscribers = Subscriber.objects.filter(confirmed=True)
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        for sub in subscribers:
            message = Mail(
                    from_email=settings.FROM_EMAIL,
                    to_emails=sub.email,
                    subject="New blog post on Studio413!",
                    html_content=(
                        '<div style="background-color:rgb(0,40,110);border:10px solid rgb(0,40,110);border-radius:10px">' \
                        '<div style="background-color:rgb(193,222,227);border:10px solid rgb(193,222,227);border-radius:10px">' \
                        '<div style="background-color:white;border-radius:10px">' \
                        '<center><h3>Studio413 has published a new blog post!</h3></center>'\
                        '<br>' \
                        '<span style="margin-left:10px">Click the following link to read the new post:</span>' \
                        '<br>' \
                        '<span style="margin-left:10px"><a href="{}/{}/">{}</a></span>'\
                        '<br>' \
                        '<span style="margin-left:10px">Or, you can copy and paste the following url into your browser:</span>' \
                        '<br>' \
                        '<span style="margin-left:10px">{}/{}</span>'\
                        '<br>' \
                        '<hr><center>If you no longer wish to receive our newsletters, you can ' \
                        '<a href="{}/?email={}&conf_num={}">unsubscribe</a>.</center><br></div></div></div>').format(
                            request.build_absolute_uri('/post'),
                            self.slug,
                            self.title,
                            request.build_absolute_uri('/post'),
                            self.slug,
                            request.build_absolute_uri('/delete'),
                            sub.email,
                            sub.conf_num
                        )
                    )
            sg.send(message)

class Comment(models.Model):
    post = models.ForeignKey('blog.Post', on_delete=models.CASCADE, related_name='comments')
    author = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    text = models.TextField()
    created_date = models.DateTimeField(default=timezone.now)
    approved_comment = models.BooleanField(default=False)

    @receiver(models.signals.post_save, sender='blog.Comment')
    def execute_after_save(sender, instance, created, *args, **kwargs):
        if created:
            email_message = 'You have a new comment awaiting approval on your blog! ' \
                'To see it, click the following link:\n\n' \
                'https://www.zenstudio413.com/admin/blog/comment/ ' \
                '\n\nDo not respond to this email address. If you wish to reach the webmaster, ' \
                'forward this email, along with your message, to megan_mccarty@hotmail.com'
            send_mail(
                subject='New Comment',
                message=email_message,
                from_email='admin@zenstudio413.com',
                recipient_list=[settings.STUDIO413_EMAIL]
            )

    def approve(self):
        self.approved_comment = True
        self.save()

    def __str__(self):
        return self.text

class Subscriber(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    conf_num = models.CharField(max_length=15)
    confirmed = models.BooleanField(default=False)

    @receiver(models.signals.post_save, sender='blog.Subscriber')
    def execute_after_save(sender, instance, created, *args, **kwargs):
        if created:
            email_message = 'You have a new subscriber for your blog! ' \
                'To see who it is, click the following link:\n\n' \
                'https://www.zenstudio413.com/admin/blog/subscriber/ ' \
                '\n\nDo not respond to this email address. If you wish to reach the webmaster, ' \
                'forward this email, along with your message, to megan_mccarty@hotmail.com'
            send_mail(
                subject='New Subscriber',
                message=email_message,
                from_email='admin@zenstudio413.com',
                recipient_list=[settings.STUDIO413_EMAIL]
            )

    def __str__(self):
        return self.email + " (" + ("not " if not self.confirmed else "") + "confirmed)"

class Newsletter(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(blank=True, null=True)
    subject = models.CharField(max_length=150)
    contents = models.FileField(upload_to='uploaded_newsletters/')
    attachment = models.FileField(upload_to='email_attachments/', default='', null=True, blank=True)

    def __str__(self):
        return self.subject + " " + self.created_at.strftime("%B %d, %Y")

    def send(self, request):
        contents = self.contents.read().decode('utf-8')
        subscribers = Subscriber.objects.filter(confirmed=True)
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        for sub in subscribers:
            message = Mail(
                    from_email=settings.FROM_EMAIL,
                    to_emails=sub.email,
                    subject=self.subject,
                    html_content=contents + (
                        '<br><center>If you no longer wish to receive our newsletters, you can ' \
                        '<a href="{}/?email={}&conf_num={}">unsubscribe</a></center>.').format(
                            request.build_absolute_uri('/delete/'),
                            sub.email,
                            sub.conf_num))

            with open(self.attachment.path, 'rb') as f:
                data = f.read()
                f.close()
            encoded_file = base64.b64encode(data).decode()

            attachedFile = Attachment(
                FileContent(encoded_file),
                FileName(self.attachment.path),
                FileType('application/pdf'),
                Disposition('attachment')
            )
            message.attachment = attachedFile

            sg.send(message)