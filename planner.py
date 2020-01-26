import json
import random
import requests
import time
from sqlalchemy import Boolean, Column, create_engine, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
engine = create_engine('sqlite:///gscontrol.db')
Session = sessionmaker(bind=engine)


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    token = Column(String, nullable=True)
    is_active = Column(Boolean, default=False)

class ExposureVote(Base):
    __tablename__ = 'exposure_vote'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    challenge_id = Column(String, nullable=False)
    challenge_url = Column(String, nullable=False)
    vote_percent = Column(Integer, nullable=False)
    vote_count = Column(Integer, nullable=False)

class PlannedJoin(Base):
    __tablename__ = 'planned_join'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    challenge_id = Column(String, nullable=False)
    unixtime = Column(Integer, nullable=False)
    status = Column(String, nullable=True)

class PlannedJoinImage(Base):
    __tablename__ = 'planned_join_image'

    id = Column(Integer, primary_key=True)
    planned_join_id = Column(Integer, nullable=False)
    image_index = Column(String, nullable=False)
    image_id = Column(String, nullable=False)

class PlannedSwap(Base):
    __tablename__ = 'planned_swap'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    challenge_id = Column(String, nullable=False)
    old_img_id = Column(String, nullable=False)
    new_img_id = Column(String, nullable=False)
    unixtime = Column(Integer, nullable=False)
    status = Column(String, nullable=True)

class PlannedVote(Base):
    __tablename__ = 'planned_vote'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    challenge_id = Column(String, nullable=False)
    challenge_url = Column(String, nullable=False)
    count = Column(Integer, nullable=False)
    unixtime = Column(Integer, nullable=False)
    status = Column(String, nullable=True)

class PlannedVoteImage(Base):
    __tablename__ = 'planned_vote_image'

    id = Column(Integer, primary_key=True)
    planned_vote_id = Column(Integer, nullable=False)
    image_index = Column(String, nullable=False)
    image_member_id = Column(String, nullable=False)
    image_id = Column(String, nullable=False)

gs_base_url = 'https://gurushots.com'
gs_verification_url = gs_base_url + '/rest/get_member_joined_active_challenges'
gs_login_url = gs_base_url + '/rest/signin'
gs_challenge_submit_url = gs_base_url + '/rest/submit_to_challenge'
gs_swap_url = gs_base_url + '/rest/swap'
gs_vote_data_url = gs_base_url + '/rest/get_vote_data'
gs_vote_submit_url = gs_base_url + '/rest/submit_votes'
gs_headers = {'X-Requested-With': 'XMLHttpRequest', 'X-Env': 'WEB', 'X-Api-Version': '8'}
tokens_verified = False

def verify_tokens():
    global tokens_verified
    print('Verifying tokens for each user.')
    session = Session()
    users = session.query(User).order_by(User.id)
    print('Found ' + str(users.count()) + ' users to verify.')
    if users.count() > 0:
        i = 1
        for user in users.all():
            print('Verifying token for user ' + str(i) + '...')
            gs_token_headers = gs_headers.copy()
            gs_token_headers['X-Token'] = user.token
            request_session = requests.Session()
            request_get_page_data_response = request_session.post(gs_verification_url, headers=gs_token_headers)
            if json.loads(request_get_page_data_response.text)['success']:
                print('No need to update token for user ' + str(i) + '.')
            else:
                print('Updating token for user ' + str(i) + '.')
                gs_login_data = {'login': user.email, 'password': user.password}
                request_session.get(gs_base_url)
                request_login_response = request_session.post(gs_login_url, data=gs_login_data, headers=gs_headers)
                if json.loads(request_login_response.text)['success']:
                    user.token = json.loads(request_login_response.text)['token']
                    session.commit()
                    print('Token for user ' + str(i) + ' has been successfully updated.')
                else:
                    print('There was an error updating a token for user ' + str(i) + ' (ID: ' + str(user.id) + ').')
            i += 1
    tokens_verified = True
    print('Tokens verification complete.')

def join():
    session = Session()
    current_time = int(time.time())
    scheduled_joins = session.query(PlannedJoin).filter(PlannedJoin.status == 'planned').filter(PlannedJoin.unixtime <= current_time).order_by(PlannedJoin.id)
    print('Found ' + str(scheduled_joins.count()) + ' scheduled joins to process.')
    if scheduled_joins.count() > 0:
        if not tokens_verified:
            verify_tokens()
        si = 1
        for join in scheduled_joins.all():
            print('Processing join ' + str(si) + '...')
            user = session.query(User).filter(User.id == join.user_id).first()
            gs_token_headers = gs_headers.copy()
            gs_token_headers['X-Token'] = user.token
            data = {
                'c_id': join.challenge_id,
                'el': 'open_challenges',
                'el_id': 'true',
            }
            images = session.query(PlannedJoinImage).filter(PlannedJoinImage.planned_join_id == join.id).order_by(PlannedJoinImage.image_index).all()
            i = 0
            for image in images:
                data['image_ids[' + str(i) + ']'] = image.image_id
                i += 1
            request_session = requests.Session()
            request_session.post(gs_challenge_submit_url, data=data, headers=gs_token_headers)
            for image in images:
                session.delete(image)
                session.commit()
            session.delete(join)
            session.commit()
            si += 1
    print('Scheduled joins have been processed.')
    session.close()

def swap():
    session = Session()
    current_time = int(time.time())
    scheduled_swaps = session.query(PlannedSwap).filter(PlannedSwap.status == 'planned').filter(PlannedSwap.unixtime <= current_time).order_by(PlannedSwap.id)
    print('Found ' + str(scheduled_swaps.count()) + ' scheduled swaps to process.')
    if scheduled_swaps.count() > 0:
        if not tokens_verified:
            verify_tokens()
        si = 1
        for swap in scheduled_swaps.all():
            print('Processing swap ' + str(si) + '...')
            user = session.query(User).filter(User.id == swap.user_id).first()
            gs_token_headers = gs_headers.copy()
            gs_token_headers['X-Token'] = user.token
            request_session = requests.Session()
            swap_data = {
                'c_id': swap.challenge_id,
                'el': 'my_challenges_current',
                'el_id': 'true',
                'img_id': swap.old_img_id,
                'new_img_id': swap.new_img_id,
            }
            swap_response = request_session.post(gs_swap_url, data=swap_data, headers=gs_token_headers)
            if json.loads(swap_response.text)['success']:
                session.delete(swap)
                session.commit()
            si += 1
    print('Scheduled swaps have been processed.')
    session.close()

def vote():
    session = Session()
    current_time = int(time.time())
    scheduled_votes = session.query(PlannedVote).filter(PlannedVote.status == 'planned').filter(PlannedVote.unixtime <= current_time).order_by(PlannedVote.id)
    print('Found ' + str(scheduled_votes.count()) + ' scheduled votes to process.')
    if scheduled_votes.count() > 0:
        if not tokens_verified:
            verify_tokens()
        users_image_ids = get_users_image_ids()
        si = 1
        for vote in scheduled_votes.all():
            print('Processing vote ' + str(si) + '...')
            user = session.query(User).filter(User.id == vote.user_id).first()
            gs_token_headers = gs_headers.copy()
            gs_token_headers['X-Token'] = user.token
            request_session = requests.Session()
            vote_data = {
                'c_id': vote.challenge_id,
                'limit': '100',
                'url': vote.challenge_url
            }
            voting_list = request_session.post(gs_vote_data_url, data=vote_data, headers=gs_token_headers)
            if json.loads(voting_list.text)['success']:
                data = {
                    'c_id': vote.challenge_id,
                    'c_token': '03AOLTBLRTGUYgYJnrxxxXTs3IdLq1pH3Qt5KSifNcfMz0HzdSKQYDpoag-eYaqUQaFbiKm8Yft1sBBCBE9iled0FV7HOINASN3RJCzGfnQZbhWqqaGQ3MqxIs_T2vo7zPIpH7gMmxoaF2YFhuKW8rPQCNauy6H1FQBATyHLtX0YRZongGJkCqkQL-J5N03wi-y6pgL8vIldNXUllBtwq9Hz8HbkdLoK-XU8d1Px_V_7mDpCS8pQyC1qT1Km1-NFZUHKhwVxlbZ-TBFPGRGuynNx-tkHc-0aLgZ8kMGGfkPEjkHb_aGJ9p7iEK2n94N6iLIqOzl_O2QlJ9U6J9NLnV7xTq7N4dfMrgPJuJ-T7hZWeaVXVnDKUqjDiZFVlKohcQbGyNczhgDrGcoHuUfrrcZrLk8s-ZU1_bXtQe9N0o5PGg8MtTpGd8yy-l99Fsnyn--3w623nKFDAj',
                }
                # images = session.query(PlannedVoteImage).filter(PlannedVoteImage.planned_vote_id == vote.id).order_by(PlannedVoteImage.image_index).all()
                i = 0
                # for image in images:
                #     for voting_image in json.loads(voting_list.text)['images']:
                #         if image.image_id == voting_image['id']:
                #             data['image_ids[' + str(i) + ']'] = image.image_id
                #             i += 1
                for user_image in users_image_ids:
                    for voting_image in json.loads(voting_list.text)['images']:
                        if user_image == voting_image['token']:
                            data['tokens[' + str(i) + ']'] = user_image
                            data['viewed_tokens[' + str(i) + ']'] = user_image
                            i += 1
                images = json.loads(voting_list.text)['images']
                random_count = int(vote.count)
                if len(images) < (random_count + i):
                    random_count = len(images) - i
                random_numbers = random.sample(range(len(images)), random_count)
                for number in random_numbers:
                    data['tokens[' + str(i) + ']'] = images[number]['token']
                    data['viewed_tokens[' + str(i) + ']'] = images[number]['token']
                    i += 1
                if 'tokens[0]' in data:
                    request_session.post(gs_vote_submit_url, data=data, headers=gs_token_headers)
                # for image in images:
                #     session.delete(image)
                #     session.commit()
                session.delete(vote)
                session.commit()
            si += 1
    print('Scheduled votes have been processed.')
    session.close()

def autovote():
    session = Session()
    exposure_votes = session.query(ExposureVote).order_by(ExposureVote.id)
    print('Found ' + str(exposure_votes.count()) + ' exposure votes to process.')
    if exposure_votes.count() > 0:
        if not tokens_verified:
            verify_tokens()
        si = 1
        for vote in exposure_votes.all():
            print('Processing exposure vote ' + str(si) + '...')
            user = session.query(User).filter(User.id == vote.user_id).first()
            gs_token_headers = gs_headers.copy()
            gs_token_headers['X-Token'] = user.token
            request_session = requests.Session()
            user_challenges_response = request_session.post(gs_verification_url, headers=gs_token_headers)
            user_challenges = json.loads(user_challenges_response.text)['challenges']
            current_exposure = 100
            challenge_found = False
            for challenge in user_challenges:
                if int(vote.challenge_id) == int(challenge['id']):
                    current_exposure = int(challenge['member']['ranking']['exposure']['exposure_factor'])
                    challenge_found = True
            if not challenge_found:
                planned_join = session.query(PlannedJoin).filter(PlannedJoin.challenge_id == vote.challenge_id).first()
                if not planned_join:
                    session.delete(vote)
                    session.commit()
            if current_exposure <= vote.vote_percent:
                print('Voting...')
                vote_data = {
                    'c_id': vote.challenge_id,
                    'limit': '100',
                    'url': vote.challenge_url
                }
                voting_list = request_session.post(gs_vote_data_url, data=vote_data, headers=gs_token_headers)
                if json.loads(voting_list.text)['success']:
                    data = {
                        'c_id': vote.challenge_id,
                        'c_token': '03AOLTBLRTGUYgYJnrxxxXTs3IdLq1pH3Qt5KSifNcfMz0HzdSKQYDpoag-eYaqUQaFbiKm8Yft1sBBCBE9iled0FV7HOINASN3RJCzGfnQZbhWqqaGQ3MqxIs_T2vo7zPIpH7gMmxoaF2YFhuKW8rPQCNauy6H1FQBATyHLtX0YRZongGJkCqkQL-J5N03wi-y6pgL8vIldNXUllBtwq9Hz8HbkdLoK-XU8d1Px_V_7mDpCS8pQyC1qT1Km1-NFZUHKhwVxlbZ-TBFPGRGuynNx-tkHc-0aLgZ8kMGGfkPEjkHb_aGJ9p7iEK2n94N6iLIqOzl_O2QlJ9U6J9NLnV7xTq7N4dfMrgPJuJ-T7hZWeaVXVnDKUqjDiZFVlKohcQbGyNczhgDrGcoHuUfrrcZrLk8s-ZU1_bXtQe9N0o5PGg8MtTpGd8yy-l99Fsnyn--3w623nKFDAj',
                    }
                    images = json.loads(voting_list.text)['images']
                    random_count = int(vote.vote_count)
                    if len(images) < random_count:
                        random_count = len(images)
                    random_numbers = random.sample(range(len(images)), random_count)
                    i = 0
                    for number in random_numbers:
                        data['tokens[' + str(i) + ']'] = images[number]['token']
                        data['viewed_tokens[' + str(i) + ']'] = images[number]['token']
                        i += 1
                    users_image_ids = get_users_image_ids()
                    for user_image in users_image_ids:
                        for list_image in images:
                            if user_image == list_image['token']:
                                data['image_ids[' + str(i) + ']'] = user_image
                                i += 1
                    request_session.post(gs_vote_submit_url, data=data, headers=gs_token_headers)
            else:
                print('Voting not needed.')
            si += 1
    print('Exposure votes have been processed.')
    session.close()

def get_users_image_ids():
    session = Session()
    users = session.query(User).order_by(User.id)
    image_ids = []
    if users.count() > 0:
        for user in users.all():
            headers = gs_headers.copy()
            headers['X-Token'] = user.token
            request_session = requests.Session()
            response = request_session.post(gs_verification_url, headers=headers)
            if json.loads(response.text)['success']:
                challenges = json.loads(response.text)['challenges']
                for challenge in challenges:
                    for entry in challenge['member']['ranking']['entries']:
                        image_ids.append(entry['id'])
    return image_ids

join()
swap()
vote()
autovote()
