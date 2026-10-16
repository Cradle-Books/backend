from django.db import models
from django.conf import settings

# Create your models here.
class Conversation(models.Model): #represents a whole conversation between two users
    participants = models.ManyToManyField( #a conversation has multiple participants, and a user can belong to multiple conversations
        settings.AUTH_USER_MODEL,
        related_name = 'conversations' #retrievable with user.conversations.all()
        )
    created_at = models.DateTimeField(auto_now_add = True)
    
class Message(models.Model): #represents a single text in a conversation
    conversation = models.ForeignKey(
        Conversation,
        on_delete = models.CASCADE, #if a conversation is deleted, all messages in it are deleted too
        related_name = 'messages' #retrievable with conversation.messages.all()
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete = models.CASCADE, #if a user is deleted, all messages sent by them are deleted too
        related_name = 'sent_messages' #retrievable with user.sent_messages.all()
    )
    content = models.TextField() #the text
    created_at = models.DateTimeField(auto_now_add = True) #when the message was sent
     #retrievable with conversation.messages.all()

    class Meta:
        ordering = ['created_at', 'id'] #messages are ordered by creation time, and then by id to break ties

