from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest
import json
from ngmail.models import NGUser, NGMessage, NGMessageFolder
from django.views.decorators.csrf import csrf_exempt
import time
from datetime import date


# Create your views here.

def message_to_dict(msg, user=None):
    return {
        'id': msg.id,
        'sender': msg.sender.id,
        'recipient': msg.recipient.id,
        'text': msg.text,
        'sent': str(msg.date_and_time),
        'folderId': msg.folder.id,
        'type': 'none' if user is None else ('sent' if msg.sender.id == user.id else 'received')
    }


def user_to_dict(usr):
    return {
        'id': usr.id,
        'firstName': usr.first_name,
        'lastName': usr.last_name,
        'gender': usr.gender,
        'address': usr.address,
        'email': usr.email,
        'avatarUrl': usr.avatar_url,
        'birthDate': str(usr.birthdate),
        'deleted': usr.deleted
    }


def folder_to_dict(folder):
    return {
        'id': folder.id,
        'name': folder.name
    }


def parse_id(item_id):
    if isinstance(item_id, int) and item_id > 0:
        return item_id
    elif isinstance(item_id, str):
        return parse_id(int(item_id)) if item_id and item_id.isdigit() else None
    else:
        return None


def parse_date(datestr):
    return date.fromtimestamp(time.mktime(time.strptime(datestr, '%Y-%m-%d')))


@csrf_exempt
def messages(request, folder):
    me = NGUser.objects.get(first_name='Леонид')
    qset = NGMessage.filter_messages(folder, me, False)
    messages = [message_to_dict(m, me) for m in qset.all()]
    return HttpResponse(
        json.dumps(messages),
        mimetype="application/json"
    )


@csrf_exempt
def get_message(request, msgid):
    msgid = parse_id(msgid)
    if msgid is None:
        return HttpResponseBadRequest()
    message = NGMessage.get_message_by_id(msgid)
    if message is None:
        return HttpResponseBadRequest()
    me = NGUser.objects.get(first_name='Леонид')
    return HttpResponse(
        json.dumps(message_to_dict(message, me)),
        mimetype="application/json"
    )


@csrf_exempt
def users(request):
    users = [user_to_dict(u) for u in NGUser.objects.filter(deleted=False)]
    return HttpResponse(
        json.dumps(users),
        mimetype="application/json"
    )


@csrf_exempt
def user(request, uid):
    uid = parse_id(uid)
    if uid is None:
        return HttpResponseBadRequest()
    user = NGUser.get_user_by_id(uid)
    if user is None:
        return HttpResponseBadRequest()
    return HttpResponse(
        json.dumps(user_to_dict(user)),
        mimetype="application/json"
    )


@csrf_exempt
def deleted_users(request):
    users = [user_to_dict(u) for u in NGUser.objects.filter(deleted=True)]
    return HttpResponse(
        json.dumps(users),
        mimetype="application/json"
    )


@csrf_exempt
def folders(request):
    me = NGUser.objects.get(first_name='Леонид')
    folders = [folder_to_dict(f) for f in NGMessageFolder.objects.all()]
    for folder in folders:
        folder['messageCount'] = NGMessage.filter_messages(folder['name'], me, False).count()
    return HttpResponse(
        json.dumps(folders),
        mimetype="application/json"
    )


@csrf_exempt
def edit_user(request, uid):
    user_id = parse_id(uid)
    if user_id is None:
        return HttpResponseBadRequest()
    user = NGUser.get_user_by_id(uid)
    if user is None:
        return HttpResponseBadRequest()
    user_data = request.POST.get('user', None)
    if user_data is None:
        return HttpResponseBadRequest()
    user_data = json.loads(user_data)
    # TODO: add server validation
    user.first_name = user_data['firstName']
    user.last_name = user_data['lastName']
    user.gender = user_data['gender']
    user.birthdate = parse_date(user_data['birthDate'])
    user.avatar_url = user_data['avatarUrl']
    user.email = user_data['email']
    user.address = user_data['address']
    user.save()
    return HttpResponse(
        json.dumps(user_to_dict(user)),
        mimetype="application/json"
    )


@csrf_exempt
def add_user(request):
    user_data = request.POST.get('user', None)
    if user_data is None:
        return HttpResponseBadRequest()
    user_data = json.loads(user_data)
    # TODO: add server validation
    user = NGUser.objects.create(
        first_name=user_data['firstName'],
        last_name=user_data['lastName'],
        gender=user_data['gender'],
        birthdate=parse_date(user_data['birthDate']),
        avatar_url=user_data['avatarUrl'],
        email=user_data['email'],
        address=user_data['address']
    )
    return HttpResponse(
        json.dumps(user_to_dict(user)),
        mimetype="application/json"
    )


@csrf_exempt
def delete_contact(request, uid):
    user_id = parse_id(uid)
    if user_id is None:
        return HttpResponseBadRequest()
    user = NGUser.get_user_by_id(uid)
    if user is None:
        return HttpResponseBadRequest()
    user.deleted = True
    user.save()
    return HttpResponse(
        json.dumps(user_to_dict(user)),
        mimetype="application/json"
    )


@csrf_exempt
def activate_contact(request, uid):
    user_id = parse_id(uid)
    if user_id is None:
        return HttpResponseBadRequest()
    user = NGUser.get_user_by_id(uid)
    if user is None:
        return HttpResponseBadRequest()
    user.deleted = False
    user.save()
    return HttpResponse(
        json.dumps(user_to_dict(user)),
        mimetype="application/json"
    )


@csrf_exempt
def move_messages(request, folder):
    folder = NGMessageFolder.get_folder_by_name(folder)
    if folder is None:
        return HttpResponseBadRequest()
    message_ids = request.POST.get('messageIds', None)
    if message_ids is None:
        return HttpResponseBadRequest()
    message_ids_parsed = list(map(parse_id, json.loads(message_ids)))
    if None in message_ids_parsed:
        return HttpResponseBadRequest()
    for mid in message_ids_parsed:
        msg = NGMessage.get_message_by_id(mid)
        msg.folder = folder
        msg.save()
    return HttpResponse(
        json.dumps({'status': 'success'}),
        mimetype="application/json"
    )


@csrf_exempt
def send_message(request):
    me = NGUser.objects.get(first_name='Леонид')
    message_info = request.POST.get('messageInfo', None)
    if message_info is None:
        return HttpResponseBadRequest()
    parsed_message_info = json.loads(message_info)
    sender = NGUser.get_user_by_id(parsed_message_info['senderId'])
    if sender is None:
        return HttpResponseBadRequest()
    recipients = [NGUser.get_user_by_id(parse_id(rid)) for rid in parsed_message_info['recipients']]
    sent_folder = NGMessageFolder.get_folder_by_name('sent' if me.id == sender.id else 'inbox')
    text = parsed_message_info['text']
    for rec in recipients:
        NGMessage.objects.create(sender=sender, folder=sent_folder, recipient=rec, text=text)
    return HttpResponse(
        json.dumps({'status': 'success'}),
        mimetype="application/json"
    )


@csrf_exempt
def create_folder(request, name):
    folder = NGMessageFolder.get_folder_by_name(name)
    if folder is not None:
        return HttpResponseBadRequest()
    NGMessageFolder.objects.create(name=name)
    return HttpResponse(
        json.dumps({'status': 'success'}),
        mimetype="application/json"
    )


@csrf_exempt
def delete_folder(request, name):
    if name.lower() in ['inbox', 'sent', 'trash', 'spam']:
        return HttpResponseBadRequest()
    folder = NGMessageFolder.get_folder_by_name(name)
    if folder is None:
        return HttpResponseBadRequest()
    fmessages = NGMessage.objects.filter(folder__name=name).count()
    if fmessages > 0:
        return HttpResponseBadRequest()
    folder.delete()
    return HttpResponse(
        json.dumps({'status': 'success'}),
        mimetype="application/json"
    )
