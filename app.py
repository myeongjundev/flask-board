from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlencode
from urllib.request import Request, urlopen

# 실행한 터미널의 위치와 관계없이 app.py 옆의 .env를 읽는다.
# 기존 셸 환경변수는 유지한다.
load_dotenv(Path(__file__).resolve().parent / '.env')

app = Flask(__name__)

# MySQL 연결 설정 (기존 MySQL 서버 mysql-lab의 새 스키마, 포트 3306)
app.config['SQLALCHEMY_DATABASE_URI'] = (
    'mysql+pymysql://root:123456@127.0.0.1:3306/my_new_board_db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'super-secret-key-change-this-to-a-long-random-value'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=2)

db = SQLAlchemy(app)
jwt = JWTManager(app)

BUSAN_TRAVEL_API_URL = (
    'https://apis.data.go.kr/6260000/RecommendedService/getRecommendedKr'
)


def fetch_busan_travel(content_id=None):
    """부산 테마여행 국문 정보를 최대 100건 조회한다."""
    service_key = (
        os.getenv('DATA_GO_KR_SERVICE_KEY', '').strip()
        or os.getenv('TOURKEY', '').strip()
    )
    if not service_key:
        # PowerShell에서 밑줄 앞에 역슬래시를 붙여 만든 변수도 실습 중 허용한다.
        service_key = next(
            (
                value.strip()
                for name, value in os.environ.items()
                if name.replace('\\', '') == 'DATA_GO_KR_SERVICE_KEY'
                and value.strip()
            ),
            '',
        )
    if not service_key:
        raise RuntimeError(
            'TOURKEY 또는 DATA_GO_KR_SERVICE_KEY 환경변수에 공공데이터포털 '
            '일반 인증키를 설정해주세요.'
        )

    # 포털의 Encoding 키가 들어와도 한 번만 인코딩되도록 원문으로 되돌린다.
    if '%' in service_key:
        service_key = unquote(service_key)

    query = urlencode({
        'serviceKey': service_key,
        'numOfRows': 100,
        'pageNo': 1,
        'resultType': 'json',
        **({'UC_SEQ': content_id} if content_id else {}),
    })
    api_request = Request(
        f'{BUSAN_TRAVEL_API_URL}?{query}',
        headers={'User-Agent': 'flask-board-busan-travel-practice/1.0'},
    )

    try:
        with urlopen(api_request, timeout=10) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f'공공데이터 API 호출에 실패했습니다: {exc}') from exc

    api_result = payload.get('getRecommendedKr')
    if api_result is None:
        api_result = payload.get('response', {})

    header = api_result.get('header', {})
    result_code = header.get('code', header.get('resultCode', '00'))
    if str(result_code) != '00':
        message = header.get(
            'message',
            header.get('resultMsg', '알 수 없는 API 오류'),
        )
        raise RuntimeError(f'공공데이터 API 오류: {message}')

    items = api_result.get('item')
    if items is None:
        items = api_result.get('body', {}).get('items', [])
    if isinstance(items, dict):
        items = items.get('item', [])
    if not isinstance(items, list):
        return []

    for item in items:
        for image_field in ('MAIN_IMG_NORMAL', 'MAIN_IMG_THUMB'):
            image_url = item.get(image_field)
            if image_url and image_url.startswith('/'):
                item[image_field] = f'https://www.visitbusan.net{image_url}'
    return items


# ----------------- Database Models -----------------
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, default='일반')
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    author = db.relationship('User', backref=db.backref('posts', lazy=True))


with app.app_context():
    db.create_all()


# ----------------- Auth Endpoints -----------------
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"msg": "이미 존재하는 사용자입니다."}), 400

    hashed_password = generate_password_hash(data['password'])
    new_user = User(username=data['username'], password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"msg": "회원가입 성공"}), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({"msg": "아이디 또는 비밀번호가 잘못되었습니다."}), 401

    access_token = create_access_token(identity=str(user.id))
    return jsonify(access_token=access_token, username=user.username)


# ----------------- Post Endpoints (RESTful) -----------------
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/public-post')
@app.route('/busan-travel')
def busan_travel_list():
    try:
        travels = fetch_busan_travel()
        error = None
    except RuntimeError as exc:
        travels = []
        error = str(exc)

    return render_template(
        'busan_travel_list.html',
        travels=travels,
        error=error,
    )


@app.route('/public-post/<content_id>')
@app.route('/busan-travel/<content_id>')
def busan_travel_detail(content_id):
    try:
        travels = fetch_busan_travel(content_id)
        travel = next(
            (item for item in travels if str(item.get('UC_SEQ')) == content_id),
            travels[0] if travels else None,
        )
        error = None if travel else '해당 테마여행 정보를 찾을 수 없습니다.'
    except RuntimeError as exc:
        travel = None
        error = str(exc)

    return render_template(
        'busan_travel_detail.html',
        travel=travel,
        content_id=content_id,
        error=error,
    )


# 목록 조회 (검색, 필터, 커서 기반 페이징)
@app.route('/api/posts', methods=['GET'])
def get_posts():
    cursor = request.args.get('cursor', type=int)
    limit = request.args.get('limit', default=5, type=int)
    search = request.args.get('search', default='', type=str)
    category = request.args.get('category', default='', type=str)

    query = Post.query

    # 카테고리 필터
    if category and category != '전체':
        query = query.filter(Post.category == category)

    # 검색 기능 (제목 또는 내용)
    if search:
        query = query.filter(
            (Post.title.like(f'%{search}%')) | (Post.content.like(f'%{search}%'))
        )

    # 커서 기반 페이징 (ID 내림차순 기준 이전 데이터 로드)
    if cursor:
        query = query.filter(Post.id < cursor)

    posts = query.order_by(Post.id.desc()).limit(limit + 1).all()

    has_more = len(posts) > limit
    if has_more:
        posts = posts[:limit]
        next_cursor = posts[-1].id
    else:
        next_cursor = None

    results = []
    for p in posts:
        results.append({
            "id": p.id,
            "title": p.title,
            "content": p.content,
            "category": p.category,
            "author": p.author.username,
            "author_id": p.author_id,
        })

    return jsonify({
        "posts": results,
        "next_cursor": next_cursor,
        "has_more": has_more,
    })


# 게시글 작성
@app.route('/api/posts', methods=['POST'])
@jwt_required()
def create_post():
    current_user_id = int(get_jwt_identity())
    data = request.get_json()

    new_post = Post(
        title=data['title'],
        content=data['content'],
        category=data.get('category', '일반'),
        author_id=current_user_id,
    )
    db.session.add(new_post)
    db.session.commit()
    return jsonify({"msg": "게시글이 등록되었습니다."}), 201


# 게시글 수정
@app.route('/api/posts/<int:id>', methods=['PUT'])
@jwt_required()
def update_post(id):
    current_user_id = int(get_jwt_identity())
    post = Post.query.get_or_404(id)

    if post.author_id != current_user_id:
        return jsonify({"msg": "권한이 없습니다."}), 403

    data = request.get_json()
    post.title = data.get('title', post.title)
    post.content = data.get('content', post.content)
    post.category = data.get('category', post.category)
    db.session.commit()

    return jsonify({"msg": "수정되었습니다."})


# 게시글 삭제
@app.route('/api/posts/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_post(id):
    current_user_id = int(get_jwt_identity())
    post = Post.query.get_or_404(id)

    if post.author_id != current_user_id:
        return jsonify({"msg": "권한이 없습니다."}), 403

    db.session.delete(post)
    db.session.commit()

    return jsonify({"msg": "삭제되었습니다."})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
