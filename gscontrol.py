import json
import requests
import time
from flask import abort, flash, Flask, redirect, render_template, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_mapping(
    SECRET_KEY = 'dev',
    SQLALCHEMY_DATABASE_URI = 'sqlite:///gscontrol.db',
    SQLALCHEMY_TRACK_MODIFICATIONS = False,
)
db = SQLAlchemy(app)

gs_base_url = 'https://gurushots.com'
gs_login_url = gs_base_url + '/rest/signin'
gs_get_page_data_url = gs_base_url + '/rest/get_page_data'
gs_active_challenges_url = gs_base_url + '/rest/get_member_joined_active_challenges'
gs_top_photos_url = gs_base_url + '/rest/get_top_photos'
gs_photos_participating_url = gs_base_url + '/rest/get_member_challenge_result'
gs_swap_url = gs_base_url + '/rest/swap'
gs_vote_data_url = gs_base_url + '/rest/get_vote_data'
gs_vote_submit_url = gs_base_url + '/rest/submit_votes'
gs_open_challenges_url = gs_base_url + '/rest/get_member_challenges'
gs_upload_restrictions_url = gs_base_url + '/rest/get_upload_restrictions'
gs_account_photos_url = gs_base_url + '/rest/get_photos_private'
gs_upload_url = 'https://uploader.gurushots.com/rest/upload_image/'
gs_unlock_url = gs_base_url + '/rest/key_unlock'
gs_challenge_submit_url = gs_base_url + '/rest/submit_to_challenge'
gs_add_profile_image_url = gs_base_url + '/rest/add_profile_image'
gs_headers = {'X-Requested-With': 'XMLHttpRequest', 'X-Env': 'WEB', 'X-Api-Version': '8'}
gs_open_challenges_data = {'filter': 'open'}


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    token = db.Column(db.String, nullable=True)
    is_active = db.Column(db.Boolean, default=False)

class ExposureVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    challenge_id = db.Column(db.String, nullable=False)
    challenge_url = db.Column(db.String, nullable=False)
    vote_percent = db.Column(db.Integer, nullable=False)
    vote_count = db.Column(db.Integer, nullable=False)

class PlannedJoin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    challenge_id = db.Column(db.String, nullable=False)
    unixtime = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String, nullable=True)

class PlannedJoinImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    planned_join_id = db.Column(db.Integer, nullable=False)
    image_index = db.Column(db.String, nullable=False)
    image_id = db.Column(db.String, nullable=False)

class PlannedSwap(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    challenge_id = db.Column(db.String, nullable=False)
    old_img_id = db.Column(db.String, nullable=False)
    new_img_id = db.Column(db.String, nullable=False)
    unixtime = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String, nullable=True)

class PlannedVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    challenge_id = db.Column(db.String, nullable=False)
    challenge_url = db.Column(db.String, nullable=False)
    count = db.Column(db.Integer, nullable=False)
    unixtime = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String, nullable=True)

class PlannedVoteImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    planned_vote_id = db.Column(db.Integer, nullable=False)
    image_index = db.Column(db.String, nullable=False)
    image_member_id = db.Column(db.String, nullable=False)
    image_id = db.Column(db.String, nullable=False)


@app.route('/', methods=['GET'])
def users_list():
    active_user = User.query.filter_by(is_active=True).first()
    users = User.query.all()
    return render_template('users_list.html', active_user=active_user, users=users)

@app.route('/login/<id>/', methods=['GET'])
def users_login(id):
    active_user = User.query.filter_by(is_active=True).first()
    if active_user:
        active_user.is_active = False
        db.session.commit()
    active_user = User.query.filter_by(id=id).first()
    if active_user:
        active_user.is_active = True
        db.session.commit()
    return redirect('/')

@app.route('/logout/', methods=['GET'])
def users_logout():
    active_user = User.query.filter_by(is_active=True).first()
    if active_user:
        active_user.is_active = False
        db.session.commit()
    return redirect('/')

@app.route('/add/', methods=['GET', 'POST'])
def users_add():
    active_user = User.query.filter_by(is_active=True).first()
    if request.method == 'POST':
        gs_login_data = {'login': request.form['email'], 'password': request.form['password']}
        request_session = requests.Session()
        request_session.get(gs_base_url)
        request_login_response = request_session.post(gs_login_url, data=gs_login_data, headers=gs_headers)
        if json.loads(request_login_response.text)['success']:
            user = User.query.filter_by(email=request.form['email']).first()
            if user is None:
                user = User(email=request.form['email'], password=request.form['password'], token=json.loads(request_login_response.text)['token'])
                db.session.add(user)
                db.session.commit()
            return redirect('/')
        flash('Email or password is incorrect.')
        return render_template('users_add.html', active_user=active_user, email=request.form['email'])
    return render_template('users_add.html', active_user=active_user)

@app.route('/remove/<id>/', methods=['GET'])
def users_remove(id):
    user = User.query.filter_by(id=id).first()
    if user:
        joins = PlannedJoin.query.filter_by(user_id=user.id)
        if joins.count() > 0:
            for join in joins.all():
                join_images = PlannedJoinImage.query.filter_by(planned_join_id=join.id).all()
                for image in join_images:
                    db.session.delete(image)
                    db.session.commit()
                db.session.delete(join)
                db.session.commit()
        swaps = PlannedSwap.query.filter_by(user_id=user.id)
        if swaps.count() > 0:
            for swap in swaps:
                db.session.delete(swap)
                db.session.commit()
        votes = PlannedVote.query.filter_by(user_id=user.id)
        if votes.count() > 0:
            for vote in votes:
                vote_images = PlannedVoteImage.query.filter_by(planned_vote_id=vote.id).all()
                for image in vote_images:
                    db.session.delete(image)
                    db.session.commit()
                db.session.delete(vote)
                db.session.commit()
        exposure_vote = ExposureVote.query.filter_by(user_id=user.id).first()
        if exposure_vote:
            db.session.delete(exposure_vote)
            db.session.commit()
        db.session.delete(user)
        db.session.commit()
    return redirect('/')

@app.route('/vote_for_all/', methods=['GET'])
def vote_for_all():
    users = User.query.order_by(User.id)
    user_image_ids = {}
    if users.count() > 0:
        for user in users.all():
            user_image_ids[user.id] = {}
            # check for actual tokens
            gs_login_data = {'login': user.email, 'password': user.password}
            request_session = requests.Session()
            request_session.get(gs_base_url)
            request_login_response = request_session.post(gs_login_url, data=gs_login_data, headers=gs_headers)
            if json.loads(request_login_response.text)['success']:
                user.token = json.loads(request_login_response.text)['token']
                db.session.commit()
            # get all active challenges
            gs_token_headers = gs_headers.copy()
            gs_token_headers['X-Token'] = user.token
            request_active_challenges_response = request_session.post(gs_active_challenges_url, headers=gs_token_headers)
            if json.loads(request_active_challenges_response.text)['success']:
                for challenge in json.loads(request_active_challenges_response.text)['challenges']:
                    user_image_ids[user.id][challenge['id']] = {
                        'url': challenge['url'],
                        'images': {},
                    }
                    # get all images
                    i = 1
                    for image in challenge['member']['ranking']['entries']:
                        user_image_ids[user.id][challenge['id']]['images'][i] = image['id']
                        i += 1
    else:
        flash('There is no users to check.')
        return redirect('/')
    # vote
    if users.count() > 0:
        for user in users.all():
            for dict_user in user_image_ids[user.id]:
                if len(user_image_ids[user.id]) > 0:
                    for voting_user in users.all():
                        if voting_user.id != user.id:
                            for challenge_id, value in user_image_ids[user.id].items():
                                gs_token_headers = gs_headers.copy()
                                gs_token_headers['X-Token'] = voting_user.token
                                request_session = requests.Session()
                                vote_data = {
                                    'c_id': challenge_id,
                                    'limit': '100',
                                    'url': user_image_ids[user.id][challenge_id]['url']
                                }
                                voting_list = request_session.post(gs_vote_data_url, data=vote_data, headers=gs_token_headers)
                                if json.loads(voting_list.text)['success']:
                                    data = {
                                        'c_id': challenge_id,
                                    }
                                    i = 0
                                    for voting_image in json.loads(voting_list.text)['images']:
                                        for image in value['images']:
                                            if value['images'][image] == voting_image['id']:
                                                data['image_ids[' + str(i) + ']'] = value['images'][image]
                                                i += 1
                                    if 'image_ids[0]' in data:
                                        request_session.post(gs_vote_submit_url, data=data, headers=gs_token_headers)
    flash('Voted successfully.')
    return redirect('/')

@app.route('/my/', methods=['GET'])
def my():
    active_user = User.query.filter_by(is_active=True).first()
    if active_user:
        gs_token_headers = gs_headers.copy()
        gs_token_headers['X-Token'] = active_user.token
        request_session = requests.Session()
        request_open_challenges_response = request_session.post(gs_open_challenges_url, data=gs_open_challenges_data, headers=gs_token_headers)
        if json.loads(request_open_challenges_response.text)['success']:
            items = sorted(json.loads(request_open_challenges_response.text)['items'], key=lambda k: (k['time_left']['hours'], k['time_left']['minutes'], k['time_left']['seconds']))
            request_get_page_data = {'url': 'https://gurushots.com/challenges/my-challenges/current'}
            request_get_page_data_response = request_session.post(gs_get_page_data_url, data=request_get_page_data, headers=gs_token_headers)
            page_data = json.loads(request_get_page_data_response.text)['items']
            request_active_challenges_response = request_session.post(gs_active_challenges_url, headers=gs_token_headers)
            active_challenges = sorted(json.loads(request_active_challenges_response.text)['challenges'], key=lambda k: (k['time_left']['hours'], k['time_left']['minutes'], k['time_left']['seconds']))
            top_photos_data = []
            photos_participating_data = []
            for active_challenge in active_challenges:
                top_photos_data_temp = {
                    'c_id': active_challenge['id'],
                    'filter': 'default',
                    'limit': '50',
                    'start': '0',
                }
                top_photos_response = request_session.post(gs_top_photos_url, data=top_photos_data_temp, headers=gs_token_headers)
                top_photos_response_parsed = json.loads(top_photos_response.text)['items'][0]
                top_photos_dict = {
                    'challenge_id': active_challenge['id'],
                    'id': top_photos_response_parsed['id'],
                    'member_id': top_photos_response_parsed['member_id'],
                    'votes': top_photos_response_parsed['votes'],
                }
                top_photos_data.append(top_photos_dict)
                photos_participating_data_temp = {
                    'c_id': active_challenge['id']
                }
                photos_participating_response = request_session.post(gs_photos_participating_url, data=photos_participating_data_temp, headers=gs_token_headers)
                photos_participating_response_parsed = json.loads(photos_participating_response.text)['challenge']['entries']
                photos_participating_dict = {
                    'challenge_id': active_challenge['id'],
                    'photos_participating': photos_participating_response_parsed
                }
                photos_participating_data.append(photos_participating_dict)
            scheduled_joins = PlannedJoin.query.filter_by(user_id=active_user.id).order_by('unixtime asc').all()
            scheduled_join_images = PlannedJoinImage.query.all()
            scheduled_swaps = PlannedSwap.query.filter_by(user_id=active_user.id).order_by('unixtime asc').all()
            scheduled_votes = PlannedVote.query.filter_by(user_id=active_user.id).order_by('unixtime asc').all()
            scheduled_vote_images = PlannedVoteImage.query.all()
            exposure_votes = ExposureVote.query.filter_by(user_id=active_user.id).all()
            exposure_votes_list = []
            for vote in exposure_votes:
                exposure_votes_list.append(vote.challenge_id)
            return render_template('my.html', active_user=active_user, page_data=page_data, active_challenges=active_challenges, top_photos=top_photos_data, photos_participating=photos_participating_data, items=items, scheduled_joins=scheduled_joins, scheduled_join_images=scheduled_join_images, scheduled_swaps=scheduled_swaps, scheduled_votes=scheduled_votes, scheduled_vote_images=scheduled_vote_images, exposure_votes=exposure_votes, exposure_votes_list=exposure_votes_list)
        else:
            gs_login_data = {'login': active_user.email, 'password': active_user.password}
            request_session = requests.Session()
            request_session.get(gs_base_url)
            request_login_response = request_session.post(gs_login_url, data=gs_login_data, headers=gs_headers)
            if json.loads(request_login_response.text)['success']:
                active_user.token = json.loads(request_login_response.text)['token']
                db.session.commit()
                return redirect('/my/')
    flash('You must log in first.')
    return redirect('/')

@app.route('/my/swap/<challenge_id>/', methods=['GET', 'POST'])
def my_swap(challenge_id):
    active_user = User.query.filter_by(is_active=True).first()
    if active_user:
        gs_token_headers = gs_headers.copy()
        gs_token_headers['X-Token'] = active_user.token
        if request.method == 'POST':
            if not len(request.form.getlist('old_photo_id')) == 1:
                flash('You need to select 1 image to swap out.')
                return redirect('/my/swap/' + challenge_id + '/')
            if not len(request.form.getlist('image_id')) == 1:
                flash('You need to select 1 image to swap out.')
                return redirect('/my/swap/' + challenge_id + '/')
            swap_request_data = {
                'c_id': challenge_id,
                'el': 'my_challenges_current',
                'el_id': 'true',
            }
            profile_request_data = {}
            oi = 0
            for old_image_id in request.form.getlist('old_photo_id'):
                swap_request_data['img_id'] = old_image_id
                oi += 1
            i = 0
            for image_id in request.form.getlist('image_id'):
                swap_request_data['new_img_id'] = image_id
                profile_request_data['image_ids[' + str(i) + ']'] = image_id
                i += 1
            request_session = requests.Session()
            request_session.post(gs_add_profile_image_url, data=profile_request_data, headers=gs_token_headers)
            request_session.post(gs_swap_url, data=swap_request_data, headers=gs_token_headers)
            flash('Successfully swapped the photo.')
            return redirect('/my/')
        request_data = {'scope': 101, 'scope_id': challenge_id}
        request_session = requests.Session()
        request_upload_restrictions_response = request_session.post(gs_upload_restrictions_url, data=request_data, headers=gs_token_headers)
        if json.loads(request_upload_restrictions_response.text)['success']:
            request_active_challenges_response = request_session.post(gs_active_challenges_url, headers=gs_token_headers)
            active_challenges = sorted(json.loads(request_active_challenges_response.text)['challenges'], key=lambda k: (k['time_left']['hours'], k['time_left']['minutes'], k['time_left']['seconds']))
            items_limit = json.loads(request_upload_restrictions_response.text)['items_limit']
            upload_token = json.loads(request_upload_restrictions_response.text)['upload_token']
            account_photos_data = {
                'c_id': challenge_id,
                'limit': '50',
                'order': 'date',
                'sort': 'desc',
                'start': '0',
                'usage': 'swap'
            }
            account_photos_response = request_session.post(gs_account_photos_url, data=account_photos_data, headers=gs_token_headers)
            account_photos = []
            if 'items' in json.loads(account_photos_response.text):
                account_photos = json.loads(account_photos_response.text)['items']
            request_get_page_data = {'url': 'https://gurushots.com/challenges/my-challenges/current'}
            request_get_page_data_response = request_session.post(gs_get_page_data_url, data=request_get_page_data, headers=gs_token_headers)
            page_data = json.loads(request_get_page_data_response.text)['items']
            return render_template('my_swap.html', active_user=active_user, page_data=page_data, challenge_id=challenge_id, items=active_challenges, items_limit=items_limit, upload_token=upload_token, account_photos=account_photos)
        else:
            gs_login_data = {'login': active_user.email, 'password': active_user.password}
            request_session = requests.Session()
            request_session.get(gs_base_url)
            request_login_response = request_session.post(gs_login_url, data=gs_login_data, headers=gs_headers)
            if json.loads(request_login_response.text)['success']:
                active_user.token = json.loads(request_login_response.text)['token']
                db.session.commit()
                return redirect('/my/swap/' + challenge_id + '/')
    flash('You must log in first.')
    return redirect('/')

@app.route('/my/auto_swap/<challenge_id>/', methods=['GET', 'POST'])
def my_auto_swap(challenge_id):
    active_user = User.query.filter_by(is_active=True).first()
    if active_user:
        gs_token_headers = gs_headers.copy()
        gs_token_headers['X-Token'] = active_user.token
        if request.method == 'POST':
            if not len(request.form.getlist('old_photo_id')) == 1:
                flash('You need to select 1 image to swap out.')
                return redirect('/my/auto_swap/' + challenge_id + '/')
            if not len(request.form.getlist('image_id')) == 1:
                flash('You need to select 1 image to swap out.')
                return redirect('/my/auto_swap/' + challenge_id + '/')
            unixtime = 0
            if 'planned_remaining' in request.form:
                days = int(request.form['planned_remaining_days'])
                hours = int(request.form['planned_remaining'].split(':')[0])
                minutes = int(request.form['planned_remaining'].split(':')[1])
                seconds = ((days * 24 * 60) + (hours * 60) + minutes) * 60
                unixtime = int(request.form['close_time']) - seconds
            elif 'planned_calendar' in request.form:
                unixtime = int(request.form['planned_calendar'])
            else:
                flash('You must choose the date for the scheduled swap.')
                return redirect('/my/auto_swap/' + challenge_id + '/')
            planned_swap = PlannedSwap(user_id=active_user.id, challenge_id=challenge_id, old_img_id=request.form.getlist('old_photo_id')[0], new_img_id=request.form.getlist('image_id')[0], unixtime=unixtime, status='planned')
            db.session.add(planned_swap)
            db.session.commit()
            profile_request_data = {}
            i = 0
            for image_id in request.form.getlist('image_id'):
                profile_request_data['image_ids[' + str(i) + ']'] = image_id
                i += 1
            request_session = requests.Session()
            request_session.post(gs_add_profile_image_url, data=profile_request_data, headers=gs_token_headers)
            flash('Successfully scheduled a swap.')
            return redirect('/my/#scheduled_swaps')
        request_data = {'scope': 101, 'scope_id': challenge_id}
        request_session = requests.Session()
        request_upload_restrictions_response = request_session.post(gs_upload_restrictions_url, data=request_data, headers=gs_token_headers)
        if json.loads(request_upload_restrictions_response.text)['success']:
            request_active_challenges_response = request_session.post(gs_active_challenges_url, headers=gs_token_headers)
            active_challenges = sorted(json.loads(request_active_challenges_response.text)['challenges'], key=lambda k: (k['time_left']['hours'], k['time_left']['minutes'], k['time_left']['seconds']))
            items_limit = json.loads(request_upload_restrictions_response.text)['items_limit']
            upload_token = json.loads(request_upload_restrictions_response.text)['upload_token']
            account_photos_data = {
                'c_id': challenge_id,
                'limit': '50',
                'order': 'date',
                'sort': 'desc',
                'start': '0',
                'usage': 'swap'
            }
            account_photos_response = request_session.post(gs_account_photos_url, data=account_photos_data, headers=gs_token_headers)
            account_photos = []
            try:
                if 'items' in json.loads(account_photos_response.text):
                    account_photos = json.loads(account_photos_response.text)['items']
            except:
                pass
            request_get_page_data = {'url': 'https://gurushots.com/challenges/my-challenges/current'}
            request_get_page_data_response = request_session.post(gs_get_page_data_url, data=request_get_page_data, headers=gs_token_headers)
            page_data = json.loads(request_get_page_data_response.text)['items']
            return render_template('my_auto_swap.html', active_user=active_user, page_data=page_data, challenge_id=challenge_id, items=active_challenges, items_limit=items_limit, upload_token=upload_token, account_photos=account_photos)
        else:
            gs_login_data = {'login': active_user.email, 'password': active_user.password}
            request_session = requests.Session()
            request_session.get(gs_base_url)
            request_login_response = request_session.post(gs_login_url, data=gs_login_data, headers=gs_headers)
            if json.loads(request_login_response.text)['success']:
                active_user.token = json.loads(request_login_response.text)['token']
                db.session.commit()
                return redirect('/my/auto_swap/' + challenge_id + '/')
    flash('You must log in first.')
    return redirect('/')

@app.route('/my/swap_preload/<challenge_id>/<start>/', methods=['GET'])
def my_swap_preload(challenge_id, start):
    active_user = User.query.filter_by(is_active=True).first()
    if active_user:
        gs_token_headers = gs_headers.copy()
        gs_token_headers['X-Token'] = active_user.token
        photos_data = {
            'c_id': challenge_id,
            'limit': '50',
            'order': 'date',
            'sort': 'desc',
            'start': start,
            'usage': 'swap'
        }
        request_session = requests.Session()
        request_photos_data_response = request_session.post(gs_account_photos_url, data=photos_data, headers=gs_token_headers)
        if json.loads(request_photos_data_response.text)['success']:
            account_photos = json.loads(request_photos_data_response.text)['items']
            return json.dumps(account_photos)
        else:
            abort(401)
    return redirect('/')

@app.route('/my/vote/<challenge_id>/<url>/', methods=['GET', 'POST'])
def my_vote(challenge_id, url):
    active_user = User.query.filter_by(is_active=True).first()
    if active_user:
        if request.method == 'POST':
            gs_token_headers = gs_headers.copy()
            gs_token_headers['X-Token'] = active_user.token
            if len(request.form.getlist('images')) < 1:
                flash('You need to vote for at least 1 photo.')
                return redirect('/my/vote/' + challenge_id + '/' + url + '/')
            data = {
                'c_id': challenge_id,
            }
            i = 0
            for image_id in request.form.getlist('images'):
                data['image_ids[' + str(i) + ']'] = image_id
                i += 1
            session = requests.Session()
            session.post(gs_vote_submit_url, data=data, headers=gs_token_headers)
            flash('Successfully voted for selected photos.')
            return redirect('/my/')
        gs_token_headers = gs_headers.copy()
        gs_token_headers['X-Token'] = active_user.token
        request_session = requests.Session()
        vote_data = {
            'c_id': challenge_id,
            'limit': '100',
            'url': url
        }
        print("-----------------------------------***********************************")
        request_vote_data_response = request_session.post(gs_vote_data_url, data=vote_data, headers=gs_token_headers)
        if json.loads(request_vote_data_response.text)['success']:
            request_get_page_data = {'url': 'https://gurushots.com/challenges/my-challenges/current'}
            request_get_page_data_response = request_session.post(gs_get_page_data_url, data=request_get_page_data, headers=gs_token_headers)
            page_data = json.loads(request_get_page_data_response.text)['items']
            request_active_challenges_response = request_session.post(gs_active_challenges_url, headers=gs_token_headers)
            active_challenges = sorted(json.loads(request_active_challenges_response.text)['challenges'], key=lambda k: (k['time_left']['hours'], k['time_left']['minutes'], k['time_left']['seconds']))
            voting_challenge = json.loads(request_vote_data_response.text)
            inactive_users_image_ids = my_vote_inactive_images()
            print("+++++++++++                 1")
            print(page_data)
            print("+++++++++++                 2")
            print(active_challenges)
            print("+++++++++++                 3")
            print(voting_challenge)
            print("+++++++++++                 4")
            print(inactive_users_image_ids)
            return render_template('my_vote.html', active_user=active_user, page_data=page_data, active_challenges=active_challenges, voting_challenge=voting_challenge, inactive_users_image_ids=inactive_users_image_ids)
        else:
            gs_login_data = {'login': active_user.email, 'password': active_user.password}
            request_session = requests.Session()
            request_session.get(gs_base_url)
            request_login_response = request_session.post(gs_login_url, data=gs_login_data, headers=gs_headers)
            if json.loads(request_login_response.text)['success']:
                active_user.token = json.loads(request_login_response.text)['token']
                db.session.commit()
                return redirect('/my/vote/' + challenge_id + '/' + url + '/')
    flash('You must log in first.')
    return redirect('/')

# @app.route('/my/vote_later/<challenge_id>/<url>/', methods=['GET', 'POST'])
# def my_vote_later(challenge_id, url):
#     active_user = User.query.filter_by(is_active=True).first()
#     if active_user:
#         if request.method == 'POST':
#             if len(request.form.getlist('images')) < 1:
#                 flash('You need to vote for at least 1 photo.')
#                 return redirect('/my/vote_later/' + challenge_id + '/' + url + '/')
#             unixtime = 0
#             if 'planned_remaining' in request.form:
#                 days = int(request.form['planned_remaining_days'])
#                 hours = int(request.form['planned_remaining'].split(':')[0])
#                 minutes = int(request.form['planned_remaining'].split(':')[1])
#                 seconds = ((days * 24 * 60) + (hours * 60) + minutes) * 60
#                 unixtime = int(request.form['close_time']) - seconds
#             elif 'planned_calendar' in request.form:
#                 unixtime = int(request.form['planned_calendar'])
#             else:
#                 flash('You must choose the date for the scheduled vote.')
#                 return redirect('/my/vote_later/' + challenge_id + '/' + url + '/')
#             planned_vote = PlannedVote(user_id=active_user.id, challenge_id=challenge_id, challenge_url=url, unixtime=unixtime, status='planned')
#             db.session.add(planned_vote)
#             db.session.commit()
#             i = 0
#             for image_id in request.form.getlist('images'):
#                 member_id = image_id.split('___')[0]
#                 photo_id = image_id.split('___')[1]
#                 planned_vote_image = PlannedVoteImage(planned_vote_id=planned_vote.id, image_index=str(i), image_member_id=member_id, image_id=photo_id)
#                 db.session.add(planned_vote_image)
#                 db.session.commit()
#                 i += 1
#             flash('Successfully scheduled a vote for selected photos.')
#             return redirect('/my/#scheduled_votes')
#         gs_token_headers = gs_headers.copy()
#         gs_token_headers['X-Token'] = active_user.token
#         request_session = requests.Session()
#         vote_data = {
#             'c_id': challenge_id,
#             'limit': '100',
#             'url': url
#         }
#         request_vote_data_response = request_session.post(gs_vote_data_url, data=vote_data, headers=gs_token_headers)
#         if json.loads(request_vote_data_response.text)['success']:
#             request_get_page_data = {'url': 'https://gurushots.com/challenges/my-challenges/current'}
#             request_get_page_data_response = request_session.post(gs_get_page_data_url, data=request_get_page_data, headers=gs_token_headers)
#             page_data = json.loads(request_get_page_data_response.text)['items']
#             request_active_challenges_response = request_session.post(gs_active_challenges_url, headers=gs_token_headers)
#             active_challenges = sorted(json.loads(request_active_challenges_response.text)['challenges'], key=lambda k: (k['time_left']['hours'], k['time_left']['minutes'], k['time_left']['seconds']))
#             voting_challenge = json.loads(request_vote_data_response.text)
#             inactive_users_image_ids = my_vote_later_inactive_images()
#             return render_template('my_vote_later.html', active_user=active_user, page_data=page_data, active_challenges=active_challenges, voting_challenge=voting_challenge, inactive_users_image_ids=inactive_users_image_ids)
#         else:
#             gs_login_data = {'login': active_user.email, 'password': active_user.password}
#             request_session = requests.Session()
#             request_session.get(gs_base_url)
#             request_login_response = request_session.post(gs_login_url, data=gs_login_data, headers=gs_headers)
#             if json.loads(request_login_response.text)['success']:
#                 active_user.token = json.loads(request_login_response.text)['token']
#                 db.session.commit()
#                 return redirect('/my/vote_later/' + challenge_id + '/' + url + '/')
#     flash('You must log in first.')
#     return redirect('/')

@app.route('/my/vote_later/', methods=['POST'])
def my_vote_later():
    active_user = User.query.filter_by(is_active=True).first()
    if active_user:
        if (int(request.form['count']) < 1) or (int(request.form['count']) > 100):
            flash('Number of photos to vote for should be between 1 and 100.')
            return redirect('/my/')

        if 'percent' in request.form:
            if (int(request.form['percent']) < 0) or (int(request.form['percent']) > 99):
                flash('Autovote percent should be between 0 and 99.')
                return redirect('/my/')
            exposure_vote = ExposureVote.query.filter_by(user_id=active_user.id, challenge_id=request.form['challenge_id']).first()
            if exposure_vote is None:
                exposure_vote = ExposureVote(user_id=active_user.id, challenge_id=request.form['challenge_id'], challenge_url=request.form['challenge_url'], vote_percent=request.form['percent'], vote_count=request.form['count'])
                db.session.add(exposure_vote)
                db.session.commit()
                flash('Autovote has been successfully enabled.')
            else:
                exposure_vote.vote_percent = request.form['percent']
                exposure_vote.vote_count = request.form['count']
                db.session.commit()
                flash('Autovote has been successfully updated.')
            return redirect('/my/')

        unixtime = 0
        if 'planned_initial' in request.form:
            unixtime = int(time.time())
        elif 'planned_remaining' in request.form:
            days = int(request.form['planned_remaining_days'])
            hours = int(request.form['planned_remaining'].split(':')[0])
            minutes = int(request.form['planned_remaining'].split(':')[1])
            seconds = ((days * 24 * 60) + (hours * 60) + minutes) * 60
            unixtime = int(request.form['close_time']) - seconds
        elif 'planned_calendar' in request.form:
            if request.form['planned_calendar'] == '':
                flash('You must choose the date for the scheduled vote.')
                return redirect('/my/')
            unixtime = int(request.form['planned_calendar'])
        else:
            flash('You must choose the date for the scheduled vote.')
            return redirect('/my/')
        planned_vote = PlannedVote(user_id=active_user.id, challenge_id=request.form['challenge_id'], challenge_url=request.form['challenge_url'], count=request.form['count'], unixtime=unixtime, status='planned')
        db.session.add(planned_vote)
        db.session.commit()
        flash('Successfully scheduled a vote.')
        return redirect('/my/#scheduled_votes')
    flash('You must log in first.')
    return redirect('/')

def my_vote_inactive_images():
    inactive_users = User.query.filter_by(is_active=False).all()
    image_ids = []
    for user in inactive_users:
        while True:
            headers = gs_headers.copy()
            headers['X-Token'] = user.token
            session = requests.Session()
            response = session.post(gs_active_challenges_url, headers=headers)
            if json.loads(response.text)['success']:
                challenges = json.loads(response.text)['challenges']
                for challenge in challenges:
                    for entry in challenge['member']['ranking']['entries']:
                        image_ids.append(entry['id'])
                break
            else:
                data = {'login': user.email, 'password': user.password}
                session = requests.Session()
                session.get(gs_base_url)
                response = session.post(gs_login_url, data=data, headers=gs_headers)
                if json.loads(response.text)['success']:
                    user.token = json.loads(response.text)['token']
                    db.session.commit()
    return image_ids

def my_vote_later_inactive_images():
    inactive_users = User.query.filter_by(is_active=False).all()
    image_ids = []
    for user in inactive_users:
        while True:
            headers = gs_headers.copy()
            headers['X-Token'] = user.token
            session = requests.Session()
            response = session.post(gs_active_challenges_url, headers=headers)
            if json.loads(response.text)['success']:
                challenges = json.loads(response.text)['challenges']
                for challenge in challenges:
                    for entry in challenge['member']['ranking']['entries']:
                        image_id = entry['member_id'] + '___' + entry['id']
                        image_ids.append(image_id)
                break
            else:
                data = {'login': user.email, 'password': user.password}
                session = requests.Session()
                session.get(gs_base_url)
                response = session.post(gs_login_url, data=data, headers=gs_headers)
                if json.loads(response.text)['success']:
                    user.token = json.loads(response.text)['token']
                    db.session.commit()
    return image_ids

@app.route('/my/vote_preload/<challenge_id>/<url>/', methods=['GET'])
def my_vote_preload(challenge_id, url):
    active_user = User.query.filter_by(is_active=True).first()
    if active_user:
        gs_token_headers = gs_headers.copy()
        gs_token_headers['X-Token'] = active_user.token
        vote_data = {
            'c_id': challenge_id,
            'limit': '50',
            'url': url
        }
        request_session = requests.Session()
        request_vote_data_response = request_session.post(gs_vote_data_url, data=vote_data, headers=gs_token_headers)
        if json.loads(request_vote_data_response.text)['success']:
            images = json.loads(request_vote_data_response.text)['images']
            return json.dumps(images)
        else:
            abort(401)
    return redirect('/')

@app.route('/my/scheduled/challenge_join/<join_id>/', methods=['GET'])
def my_scheduled_challenge_join_cancel(join_id):
    active_user = User.query.filter_by(is_active=True).first()
    if active_user:
        scheduled_join = PlannedJoin.query.filter_by(id=join_id, user_id=active_user.id).first()
        if scheduled_join:
            scheduled_autovote = ExposureVote.query.filter_by(challenge_id=scheduled_join.challenge_id).first()
            if scheduled_autovote:
                db.session.delete(scheduled_autovote)
                db.session.commit()
            scheduled_join_images = PlannedJoinImage.query.filter_by(planned_join_id=scheduled_join.id).all()
            for image in scheduled_join_images:
                db.session.delete(image)
                db.session.commit()
            db.session.delete(scheduled_join)
            db.session.commit()
            flash('Scheduled join successfully canceled.')
        return redirect('/my/#scheduled_joins')
    flash('You must log in first.')
    return redirect('/')

@app.route('/my/scheduled/swap/<swap_id>/', methods=['GET'])
def my_scheduled_swap_cancel(swap_id):
    active_user = User.query.filter_by(is_active=True).first()
    if active_user:
        scheduled_swap = PlannedSwap.query.filter_by(id=swap_id, user_id=active_user.id).first()
        if scheduled_swap:
            db.session.delete(scheduled_swap)
            db.session.commit()
            flash('Scheduled swap successfully canceled.')
        return redirect('/my/#scheduled_swaps')
    flash('You must log in first.')
    return redirect('/')

@app.route('/my/scheduled/vote/<vote_id>/', methods=['GET'])
def my_scheduled_vote_cancel(vote_id):
    active_user = User.query.filter_by(is_active=True).first()
    if active_user:
        scheduled_vote = PlannedVote.query.filter_by(id=vote_id, user_id=active_user.id).first()
        if scheduled_vote:
            # scheduled_vote_images = PlannedVoteImage.query.filter_by(planned_vote_id=scheduled_vote.id).all()
            # for image in scheduled_vote_images:
                # db.session.delete(image)
            db.session.delete(scheduled_vote)
            db.session.commit()
            flash('Scheduled vote successfully canceled.')
        return redirect('/my/#scheduled_votes')
    flash('You must log in first.')
    return redirect('/')

@app.route('/open/', methods=['GET'])
def open():
    active_user = User.query.filter_by(is_active=True).first()
    if active_user:
        gs_token_headers = gs_headers.copy()
        gs_token_headers['X-Token'] = active_user.token
        request_session = requests.Session()
        request_open_challenges_response = request_session.post(gs_open_challenges_url, data=gs_open_challenges_data, headers=gs_token_headers)
        if json.loads(request_open_challenges_response.text)['success']:
            items = sorted(json.loads(request_open_challenges_response.text)['items'], key=lambda k: (k['time_left']['hours'], k['time_left']['minutes'], k['time_left']['seconds']))
            request_get_page_data = {'url': 'https://gurushots.com/challenges/my-challenges/current'}
            request_get_page_data_response = request_session.post(gs_get_page_data_url, data=request_get_page_data, headers=gs_token_headers)
            page_data = json.loads(request_get_page_data_response.text)['items']
            top_photos_data = []
            for active_challenge in items:
                top_photos_data_temp = {
                    'c_id': active_challenge['id'],
                    'filter': 'default',
                    'limit': '50',
                    'start': '0',
                }
                top_photos_response = request_session.post(gs_top_photos_url, data=top_photos_data_temp, headers=gs_token_headers)
                top_photos_response_parsed = json.loads(top_photos_response.text)['items'][0]
                top_photos_dict = {
                    'challenge_id': active_challenge['id'],
                    'id': top_photos_response_parsed['id'],
                    'member_id': top_photos_response_parsed['member_id'],
                    'votes': top_photos_response_parsed['votes'],
                }
                top_photos_data.append(top_photos_dict)
                if active_challenge['id'] == 11221:
                    print(top_photos_dict)
            return render_template('open_list.html', active_user=active_user, page_data=page_data, top_photos=top_photos_data, items=items)
        else:
            gs_login_data = {'login': active_user.email, 'password': active_user.password}
            request_session = requests.Session()
            request_session.get(gs_base_url)
            request_login_response = request_session.post(gs_login_url, data=gs_login_data, headers=gs_headers)
            if json.loads(request_login_response.text)['success']:
                active_user.token = json.loads(request_login_response.text)['token']
                db.session.commit()
                return redirect('/open/')
    flash('You must log in first.')
    return redirect('/')

@app.route('/open/join/<challenge_id>/', methods=['GET', 'POST'])
def open_join(challenge_id):
    active_user = User.query.filter_by(is_active=True).first()
    if active_user:
        gs_token_headers = gs_headers.copy()
        gs_token_headers['X-Token'] = active_user.token
        if request.method == 'POST':
            if len(request.form.getlist('image_id')) < 1:
                flash('You need to add at least 1 image.')
                return redirect('/open/join/' + challenge_id + '/')
            challenge_request_data = {
                'c_id': challenge_id,
                'el': 'open_challenges',
                'el_id': 'true',
            }
            profile_request_data = {}
            i = 0
            for image_id in request.form.getlist('image_id'):
                challenge_request_data['image_ids[' + str(i) + ']'] = image_id
                profile_request_data['image_ids[' + str(i) + ']'] = image_id
                i += 1
            request_session = requests.Session()
            if 'is_locked' in request.form:
                unlock_request_data = {
                    'c_id': challenge_id,
                    'usage': 'JOIN_CHALLENGE'
                }
                gs_unlock_url_response = request_session.post(gs_unlock_url, data=unlock_request_data, headers=gs_token_headers)
                if not json.loads(gs_unlock_url_response.text)['success']:
                    flash('Unable to unlock.')
                    return redirect('/open/join/' + challenge_id + '/')
            request_session.post(gs_add_profile_image_url, data=profile_request_data, headers=gs_token_headers)
            request_session.post(gs_challenge_submit_url, data=challenge_request_data, headers=gs_token_headers)
            if 'autovote_enabled' in request.form:
                exposure_vote = ExposureVote.query.filter_by(user_id=active_user.id, challenge_id=challenge_id).first()
                if exposure_vote is None:
                    exposure_vote = ExposureVote(user_id=active_user.id, challenge_id=challenge_id, challenge_url=request.form['autovote_challenge_url'], vote_percent=request.form['autovote_percent'], vote_count=request.form['autovote_count'])
                    db.session.add(exposure_vote)
                    db.session.commit()
            flash('Successfully joined to challenge.')
            return redirect('/my/')
        request_data = {'scope': 100, 'scope_id': challenge_id}
        request_session = requests.Session()
        request_upload_restrictions_response = request_session.post(gs_upload_restrictions_url, data=request_data, headers=gs_token_headers)
        if json.loads(request_upload_restrictions_response.text)['success']:
            items = ''
            request_open_challenges_response = request_session.post(gs_open_challenges_url, data=gs_open_challenges_data, headers=gs_token_headers)
            if json.loads(request_open_challenges_response.text)['success']:
                items = sorted(json.loads(request_open_challenges_response.text)['items'], key=lambda k: (k['time_left']['hours'], k['time_left']['minutes'], k['time_left']['seconds']))
            items_limit = json.loads(request_upload_restrictions_response.text)['items_limit']
            upload_token = json.loads(request_upload_restrictions_response.text)['upload_token']
            account_photos_data = {
                'c_id': challenge_id,
                'limit': '50',
                'order': 'date',
                'sort': 'desc',
                'start': '0',
                'usage': 'submit'
            }
            account_photos_response = request_session.post(gs_account_photos_url, data=account_photos_data, headers=gs_token_headers)
            account_photos = []
            if 'items' in json.loads(account_photos_response.text):
                account_photos = json.loads(account_photos_response.text)['items']
            request_get_page_data = {'url': 'https://gurushots.com/challenges/my-challenges/current'}
            request_get_page_data_response = request_session.post(gs_get_page_data_url, data=request_get_page_data, headers=gs_token_headers)
            page_data = json.loads(request_get_page_data_response.text)['items']
            return render_template('open_join.html', active_user=active_user, page_data=page_data, challenge_id=challenge_id, items=items, items_limit=items_limit, upload_token=upload_token, account_photos=account_photos)
        else:
            gs_login_data = {'login': active_user.email, 'password': active_user.password}
            request_session = requests.Session()
            request_session.get(gs_base_url)
            request_login_response = request_session.post(gs_login_url, data=gs_login_data, headers=gs_headers)
            if json.loads(request_login_response.text)['success']:
                active_user.token = json.loads(request_login_response.text)['token']
                db.session.commit()
                return redirect('/open/join/' + challenge_id + '/')
    flash('You must log in first.')
    return redirect('/')

@app.route('/open/join_later/<challenge_id>/', methods=['GET', 'POST'])
def open_join_later(challenge_id):
    active_user = User.query.filter_by(is_active=True).first()
    if active_user:
        gs_token_headers = gs_headers.copy()
        gs_token_headers['X-Token'] = active_user.token
        if request.method == 'POST':
            if len(request.form.getlist('image_id')) < 1:
                flash('You need to add at least 1 image.')
                return redirect('/open/join_later/' + challenge_id + '/')
            planned_join = PlannedJoin.query.filter_by(user_id=active_user.id, challenge_id=challenge_id).first()
            if planned_join:
                flash('You have already scheduled join for this challenge.')
                return redirect('/open/join_later/' + challenge_id + '/')
            unixtime = 0
            if 'planned_remaining' in request.form:
                days = int(request.form['planned_remaining_days'])
                hours = int(request.form['planned_remaining'].split(':')[0])
                minutes = int(request.form['planned_remaining'].split(':')[1])
                seconds = ((days * 24 * 60) + (hours * 60) + minutes) * 60
                unixtime = int(request.form['close_time']) - seconds
            elif 'planned_calendar' in request.form:
                unixtime = int(request.form['planned_calendar'])
            else:
                flash('You must choose the date for the scheduled challenge join.')
                return redirect('/open/join_later/' + challenge_id + '/')
            planned_join = PlannedJoin(user_id=active_user.id, challenge_id=challenge_id, unixtime=unixtime, status='planned')
            db.session.add(planned_join)
            db.session.commit()
            profile_request_data = {}
            i = 0
            for image_id in request.form.getlist('image_id'):
                profile_request_data['image_ids[' + str(i) + ']'] = image_id
                planned_join_image = PlannedJoinImage(planned_join_id=planned_join.id, image_index=str(i), image_id=image_id)
                db.session.add(planned_join_image)
                db.session.commit()
                i += 1
            request_session = requests.Session()
            if 'is_locked' in request.form:
                unlock_request_data = {
                    'c_id': challenge_id,
                    'usage': 'JOIN_CHALLENGE'
                }
                gs_unlock_url_response = request_session.post(gs_unlock_url, data=unlock_request_data, headers=gs_token_headers)
                if not json.loads(gs_unlock_url_response.text)['success']:
                    flash('Unable to unlock.')
                    return redirect('/open/join_later/' + challenge_id + '/')
            request_session.post(gs_add_profile_image_url, data=profile_request_data, headers=gs_token_headers)
            if 'autovote_enabled' in request.form:
                exposure_vote = ExposureVote.query.filter_by(user_id=active_user.id, challenge_id=challenge_id).first()
                if exposure_vote is None:
                    exposure_vote = ExposureVote(user_id=active_user.id, challenge_id=challenge_id, challenge_url=request.form['autovote_challenge_url'], vote_percent=request.form['autovote_percent'], vote_count=request.form['autovote_count'])
                    db.session.add(exposure_vote)
                    db.session.commit()
            flash('Successfully scheduled join to the challenge.')
            return redirect('/my/#scheduled_joins')
        request_data = {'scope': 100, 'scope_id': challenge_id}
        request_session = requests.Session()
        request_upload_restrictions_response = request_session.post(gs_upload_restrictions_url, data=request_data, headers=gs_token_headers)
        if json.loads(request_upload_restrictions_response.text)['success']:
            items = ''
            request_open_challenges_response = request_session.post(gs_open_challenges_url, data=gs_open_challenges_data, headers=gs_token_headers)
            if json.loads(request_open_challenges_response.text)['success']:
                items = sorted(json.loads(request_open_challenges_response.text)['items'], key=lambda k: (k['time_left']['hours'], k['time_left']['minutes'], k['time_left']['seconds']))
            items_limit = json.loads(request_upload_restrictions_response.text)['items_limit']
            upload_token = json.loads(request_upload_restrictions_response.text)['upload_token']
            account_photos_data = {
                'c_id': challenge_id,
                'limit': '50',
                'order': 'date',
                'sort': 'desc',
                'start': '0',
                'usage': 'submit'
            }
            account_photos_response = request_session.post(gs_account_photos_url, data=account_photos_data, headers=gs_token_headers)
            account_photos = []
            if 'items' in json.loads(account_photos_response.text):
                account_photos = json.loads(account_photos_response.text)['items']
            request_get_page_data = {'url': 'https://gurushots.com/challenges/my-challenges/current'}
            request_get_page_data_response = request_session.post(gs_get_page_data_url, data=request_get_page_data, headers=gs_token_headers)
            page_data = json.loads(request_get_page_data_response.text)['items']
            return render_template('open_join_later.html', active_user=active_user, page_data=page_data, challenge_id=challenge_id, items=items, items_limit=items_limit, upload_token=upload_token, account_photos=account_photos)
        else:
            gs_login_data = {'login': active_user.email, 'password': active_user.password}
            request_session = requests.Session()
            request_session.get(gs_base_url)
            request_login_response = request_session.post(gs_login_url, data=gs_login_data, headers=gs_headers)
            if json.loads(request_login_response.text)['success']:
                active_user.token = json.loads(request_login_response.text)['token']
                db.session.commit()
                return redirect('/open/join_later/' + challenge_id + '/')
    flash('You must log in first.')
    return redirect('/')

@app.route('/open/join_preload/<challenge_id>/<start>/', methods=['GET'])
def open_join_preload(challenge_id, start):
    active_user = User.query.filter_by(is_active=True).first()
    if active_user:
        gs_token_headers = gs_headers.copy()
        gs_token_headers['X-Token'] = active_user.token
        photos_data = {
            'c_id': challenge_id,
            'limit': '50',
            'order': 'date',
            'sort': 'desc',
            'start': start,
            'usage': 'submit'
        }
        request_session = requests.Session()
        request_photos_data_response = request_session.post(gs_account_photos_url, data=photos_data, headers=gs_token_headers)
        if json.loads(request_photos_data_response.text)['success']:
            account_photos = json.loads(request_photos_data_response.text)['items']
            return json.dumps(account_photos)
        else:
            abort(401)
    return redirect('/')

@app.route('/upload/', methods=['POST'])
def upload_images():
    active_user = User.query.filter_by(is_active=True).first()
    if (active_user) and (request.method == 'POST'):
        gs_token_headers = gs_headers.copy()
        gs_token_headers['X-Token'] = active_user.token
        request_files = {
            'qqfile': request.files['file']
        }
        request_data = {
            'qqfilename': request.form['filename'],
            'qqtotalfilesize': request.form['filesize'],
            'qquuid': request.form['upload_token']
        }
        request_session = requests.Session()
        request_upload_url_response = request_session.post(gs_upload_url + request.form['upload_token'], files=request_files, data=request_data, headers=gs_token_headers)
        if json.loads(request_upload_url_response.text)['success']:
            response = {
                'success': True,
                'image_id': json.loads(request_upload_url_response.text)['data']['id'],
                'member_id': json.loads(request_upload_url_response.text)['data']['member_id']
            }
            return json.dumps(response)
        else:
            abort(401)
    return redirect('/')

@app.route('/my/autovote/enable/', methods=['POST'])
def autovote_enable():
    active_user = User.query.filter_by(is_active=True).first()
    if active_user:
        if (int(request.form['percent']) < 0) or (int(request.form['percent']) > 99):
            flash('Autovote percent should be between 0 and 99.')
            return redirect('/my/')
        if (int(request.form['count']) < 1) or (int(request.form['count']) > 100):
            flash('Number of photos to vote for should be between 1 and 100.')
            return redirect('/my/')
        exposure_vote = ExposureVote.query.filter_by(user_id=active_user.id, challenge_id=request.form['challenge_id']).first()
        if exposure_vote is None:
            exposure_vote = ExposureVote(user_id=active_user.id, challenge_id=request.form['challenge_id'], challenge_url=request.form['challenge_url'], vote_percent=request.form['percent'], vote_count=request.form['count'])
            db.session.add(exposure_vote)
            db.session.commit()
            flash('Autovote has been successfully enabled.')
            return redirect('/my/')
        return redirect('/my/')
    flash('You must log in first.')
    return redirect('/')

@app.route('/my/autovote/update/', methods=['POST'])
def autovote_update():
    active_user = User.query.filter_by(is_active=True).first()
    if active_user:
        if (int(request.form['percent']) < 0) or (int(request.form['percent']) > 99):
            flash('Autovote percent should be between 0 and 99.')
            return redirect('/my/')
        if (int(request.form['count']) < 1) or (int(request.form['count']) > 100):
            flash('Number of photos to vote for should be between 1 and 100.')
            return redirect('/my/')
        exposure_vote = ExposureVote.query.filter_by(user_id=active_user.id, challenge_id=request.form['challenge_id']).first()
        if exposure_vote is not None:
            exposure_vote.vote_percent = request.form['percent']
            exposure_vote.vote_count = request.form['count']
            db.session.commit()
            flash('Autovote has been successfully updated.')
            return redirect('/my/')
        return redirect('/my/')
    flash('You must log in first.')
    return redirect('/')

@app.route('/my/autovote/disable/<challenge_id>/', methods=['GET'])
def autovote_disable(challenge_id):
    active_user = User.query.filter_by(is_active=True).first()
    if active_user:
        exposure_vote = ExposureVote.query.filter_by(user_id=active_user.id, challenge_id=challenge_id).first()
        if exposure_vote is not None:
            db.session.delete(exposure_vote)
            db.session.commit()
            flash('Autovote has been successfully disabled.')
            return redirect('/my/')
        return redirect('/my/')
    flash('You must log in first.')
    return redirect('/')
