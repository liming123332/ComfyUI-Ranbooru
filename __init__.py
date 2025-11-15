import os
import json
import random
import html
from typing import List, Tuple, Dict, Any

import requests

try:
    import requests_cache
    HAS_REQUESTS_CACHE = True
except Exception:
    requests_cache = None
    HAS_REQUESTS_CACHE = False


POST_AMOUNT = 100
COLORED_BG = ['black_background', 'aqua_background', 'white_background', 'colored_background', 'gray_background', 'blue_background', 'green_background', 'red_background', 'brown_background', 'purple_background', 'yellow_background', 'orange_background', 'pink_background', 'plain', 'transparent_background', 'simple_background', 'two-tone_background', 'grey_background']
ADD_BG = ['outdoors', 'indoors']
BW_BG = ['monochrome', 'greyscale', 'grayscale']

RATING_TYPES = {
    "none": {
        "All": "All"
    },
    "full": {
        "All": "All",
        "Safe": "safe",
        "Questionable": "questionable",
        "Explicit": "explicit"
    },
    "single": {
        "All": "All",
        "Safe": "g",
        "Sensitive": "s",
        "Questionable": "q",
        "Explicit": "e"
    }
}

RATINGS = {
    "e621": RATING_TYPES['full'],
    "danbooru": RATING_TYPES['single'],
    "aibooru": RATING_TYPES['full'],
    "yande.re": RATING_TYPES['full'],
    "konachan": RATING_TYPES['full'],
    "safebooru": RATING_TYPES['none'],
    "rule34": RATING_TYPES['full'],
    "xbooru": RATING_TYPES['full'],
    "gelbooru": RATING_TYPES['single']
}


class CredentialsManager:
    def __init__(self, extension_root: str):
        self.extension_root = extension_root
        self.credentials_dir = os.path.join(extension_root, 'user', 'credentials')
        self.credentials_file = os.path.join(self.credentials_dir, 'credentials.json')
        os.makedirs(self.credentials_dir, exist_ok=True)
        if not os.path.exists(self.credentials_file):
            self._save_credentials({})

    def _load_credentials(self) -> Dict[str, Any]:
        try:
            with open(self.credentials_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_credentials(self, credentials: Dict[str, Any]) -> None:
        with open(self.credentials_file, 'w', encoding='utf-8') as f:
            json.dump(credentials, f, indent=2, ensure_ascii=False)

    def get_booru_credentials(self, booru_name: str) -> Dict[str, str]:
        credentials = self._load_credentials()
        return credentials.get(booru_name, {})


extension_root = os.path.dirname(__file__)
credentials_manager = CredentialsManager(extension_root)
user_data_dir = os.path.join(extension_root, 'user')
user_search_dir = os.path.join(user_data_dir, 'search')
user_remove_dir = os.path.join(user_data_dir, 'remove')
os.makedirs(user_search_dir, exist_ok=True)
os.makedirs(user_remove_dir, exist_ok=True)
try:
    if not os.path.isfile(os.path.join(user_search_dir, 'tags_search.txt')):
        with open(os.path.join(user_search_dir, 'tags_search.txt'), 'w', encoding='utf-8'):
            pass
    if not os.path.isfile(os.path.join(user_remove_dir, 'tags_remove.txt')):
        with open(os.path.join(user_remove_dir, 'tags_remove.txt'), 'w', encoding='utf-8'):
            pass
except Exception:
    pass


class Booru:
    def __init__(self, booru: str, base_url: str):
        self.booru = booru
        self.base_url = base_url
        self.booru_url = base_url
        self.headers = {'user-agent': 'comfyui-ranbooru/1.0'}

    def get_data(self, add_tags: str, max_pages: int = 10, id: str = '') -> Dict[str, Any]:
        raise NotImplementedError

    def get_post(self, add_tags: str, max_pages: int = 10, id: str = '') -> Dict[str, Any]:
        raise NotImplementedError


class Gelbooru(Booru):
    def __init__(self, fringe_benefits: bool, api_key: str = None, user_id: str = None):
        super().__init__('gelbooru', f'https://gelbooru.com/index.php?page=dapi&s=post&q=index&json=1&limit={POST_AMOUNT}')
        self.fringeBenefits = fringe_benefits
        self.api_key = api_key
        self.user_id = user_id

    def get_data(self, add_tags: str, max_pages: int = 10, id: str = '') -> Dict[str, Any]:
        loop_msg = True
        for _ in range(2):
            if id:
                add_tags = ''
            api_params = f"&pid={random.SystemRandom().randint(0, max_pages-1)}{id}{add_tags}"
            if self.api_key and self.user_id:
                api_params += f"&api_key={self.api_key}&user_id={self.user_id}"
            url = f"{self.base_url}{api_params}"
            self.booru_url = url
            res = requests.get(url, cookies={'fringeBenefits': 'yup'}) if self.fringeBenefits else requests.get(url)
            try:
                data = res.json()
            except Exception:
                data = {'@attributes': {'count': 0}, 'post': []}
            count = data.get('@attributes', {}).get('count', 0)
            if count <= max_pages * POST_AMOUNT:
                max_pages = count // POST_AMOUNT + 1
                if loop_msg:
                    loop_msg = False
                continue
            break
        return data

    def get_post(self, add_tags: str, max_pages: int = 10, id: str = '') -> Dict[str, Any]:
        return self.get_data(add_tags, max_pages, "&id=" + id)


class XBooru(Booru):
    def __init__(self):
        super().__init__('xbooru', f'https://xbooru.com/index.php?page=dapi&s=post&q=index&json=1&limit={POST_AMOUNT}')

    def get_data(self, add_tags: str, max_pages: int = 10, id: str = '') -> Dict[str, Any]:
        for _ in range(2):
            if id:
                add_tags = ''
            url = f"{self.base_url}&pid={random.SystemRandom().randint(0, max_pages-1)}{id}{add_tags}"
            self.booru_url = url
            res = requests.get(url)
            try:
                data = res.json()
            except Exception:
                data = []
            count = 0
            for post in data:
                if isinstance(post, dict):
                    post['file_url'] = f"https://xbooru.com/images/{post.get('directory')}/{post.get('image')}"
                    count += 1
            if count <= max_pages * POST_AMOUNT:
                max_pages = count // POST_AMOUNT + 1
                continue
            break
        return {'post': data}

    def get_post(self, add_tags: str, max_pages: int = 10, id: str = '') -> Dict[str, Any]:
        return self.get_data(add_tags, max_pages, "&id=" + id)


class Rule34(Booru):
    def __init__(self, api_key: str = None, user_id: str = None):
        super().__init__('rule34', f'https://api.rule34.xxx/index.php?page=dapi&s=post&q=index&json=1&limit={POST_AMOUNT}')
        self.api_key = api_key
        self.user_id = user_id

    def get_data(self, add_tags: str, max_pages: int = 10, id: str = '') -> Dict[str, Any]:
        loop_msg = True
        for _ in range(2):
            if id:
                add_tags = ''
            url = f"{self.base_url}&pid={random.SystemRandom().randint(0, max_pages-1)}{id}{add_tags}"
            if self.api_key and self.user_id:
                url += f"&api_key={self.api_key}&user_id={self.user_id}"
            self.booru_url = url
            res = requests.get(url)
            try:
                data = res.json()
            except Exception:
                data = []
            if not isinstance(data, list):
                data = []
            count = len(data)
            if count == 0:
                max_pages = 2
                if loop_msg:
                    loop_msg = False
                continue
            break
        return {'post': data}

    def get_post(self, add_tags: str, max_pages: int = 10, id: str = '') -> Dict[str, Any]:
        return self.get_data(add_tags, max_pages, "&id=" + id)


class Safebooru(Booru):
    def __init__(self):
        super().__init__('safebooru', f'https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&limit={POST_AMOUNT}')

    def get_data(self, add_tags: str, max_pages: int = 10, id: str = '') -> Dict[str, Any]:
        for _ in range(2):
            if id:
                add_tags = ''
            url = f"{self.base_url}&pid={random.SystemRandom().randint(0, max_pages-1)}{id}{add_tags}"
            self.booru_url = url
            res = requests.get(url)
            try:
                data = res.json()
            except Exception:
                data = []
            count = 0
            for post in data:
                if isinstance(post, dict):
                    post['file_url'] = f"https://safebooru.org/images/{post.get('directory')}/{post.get('image')}"
                    count += 1
            if count <= max_pages * POST_AMOUNT:
                max_pages = count // POST_AMOUNT + 1
                continue
            break
        return {'post': data}

    def get_post(self, add_tags: str, max_pages: int = 10, id: str = '') -> Dict[str, Any]:
        return self.get_data(add_tags, max_pages, "&id=" + id)


class Konachan(Booru):
    def __init__(self):
        super().__init__('konachan', f'https://konachan.com/post.json?limit={POST_AMOUNT}')

    def get_data(self, add_tags: str, max_pages: int = 10, id: str = '') -> Dict[str, Any]:
        loop_msg = True
        for _ in range(2):
            if id:
                add_tags = ''
            url = f"{self.base_url}&page={random.SystemRandom().randint(0, max_pages-1)}{id}{add_tags}"
            self.booru_url = url
            res = requests.get(url)
            if res.status_code != 200:
                data = []
            else:
                try:
                    data = res.json()
                except Exception:
                    data = []
            count = len(data)
            if count == 0:
                max_pages = 2
                if loop_msg:
                    loop_msg = False
                continue
            break
        return {'post': data}

    def get_post(self, add_tags: str, max_pages: int = 10, id: str = '') -> Dict[str, Any]:
        raise Exception("Konachan does not support post IDs")


class Yandere(Booru):
    def __init__(self):
        super().__init__('yande.re', f'https://yande.re/post.json?api_version=2')

    def get_data(self, add_tags: str, max_pages: int = 10, id: str = '') -> Dict[str, Any]:
        loop_msg = True
        for _ in range(2):
            if id:
                add_tags = ''
            page = random.SystemRandom().randint(0, max_pages - 1)
            extras = '&filter=1&include_tags=1&include_votes=1&include_pools=1'
            url = f"{self.base_url}&limit={POST_AMOUNT}&page={page}{id}{add_tags}{extras}"
            self.booru_url = url
            res = requests.get(url)
            posts: List[Dict[str, Any]] = []
            if res.status_code == 200:
                try:
                    data = res.json()
                    if isinstance(data, dict):
                        posts = data.get('posts', [])
                    elif isinstance(data, list):
                        posts = data
                except Exception:
                    posts = []
            count = len(posts)
            if count == 0:
                max_pages = 2
                if loop_msg:
                    loop_msg = False
                continue
            break
        return {'post': posts}

    def get_post(self, add_tags: str, max_pages: int = 10, id: str = '') -> Dict[str, Any]:
        raise Exception("Yande.re does not support post IDs")


class AIBooru(Booru):
    def __init__(self):
        super().__init__('AIBooru', f'https://aibooru.online/posts.json?limit={POST_AMOUNT}')

    def get_data(self, add_tags: str, max_pages: int = 10, id: str = '') -> Dict[str, Any]:
        loop_msg = True
        for _ in range(2):
            if id:
                add_tags = ''
            url = f"{self.base_url}&page={random.SystemRandom().randint(0, max_pages-1)}{id}{add_tags}"
            self.booru_url = url
            res = requests.get(url)
            try:
                data = res.json()
            except Exception:
                data = []
            for post in data:
                if isinstance(post, dict):
                    post['tags'] = post.get('tag_string', '')
            count = len(data)
            if count == 0:
                max_pages = 2
                if loop_msg:
                    loop_msg = False
                continue
            break
        return {'post': data}

    def get_post(self, add_tags: str, max_pages: int = 10, id: str = '') -> Dict[str, Any]:
        raise Exception("AIBooru does not support post IDs")


class Danbooru(Booru):
    def __init__(self):
        super().__init__('danbooru', f'https://danbooru.donmai.us/posts.json?limit={POST_AMOUNT}')

    def get_data(self, add_tags: str, max_pages: int = 10, id: str = '') -> Dict[str, Any]:
        loop_msg = True
        for _ in range(2):
            if id:
                add_tags = ''
            url = f"{self.base_url}&page={random.randint(0, max_pages-1)}{id}{add_tags}"
            self.booru_url = url
            res = requests.get(url, headers=self.headers)
            try:
                data = res.json()
            except Exception:
                data = []
            if not isinstance(data, list):
                try:
                    data = data.get('posts', [])
                except Exception:
                    data = []
            for post in data:
                if isinstance(post, dict):
                    post['tags'] = post.get('tag_string', '')
            count = len(data)
            if count == 0:
                max_pages = 2
                if loop_msg:
                    loop_msg = False
                continue
            break
        return {'post': data}

    def get_post(self, add_tags: str, max_pages: int = 10, id: str = '') -> Dict[str, Any]:
        self.booru_url = f"https://danbooru.donmai.us/posts/{id}.json"
        res = requests.get(self.booru_url, headers=self.headers)
        try:
            data = res.json()
        except Exception:
            data = {}
        if isinstance(data, dict):
            data['tags'] = data.get('tag_string', '')
            data = {'post': [data]}
        else:
            data = {'post': []}
        return data


class e621(Booru):
    def __init__(self):
        super().__init__('e621', f'https://e621.net/posts.json?limit={POST_AMOUNT}')

    def get_data(self, add_tags: str, max_pages: int = 10, id: str = '') -> Dict[str, Any]:
        loop_msg = True
        for _ in range(2):
            if id:
                add_tags = ''
            url = f"{self.base_url}&page={random.SystemRandom().randint(0, max_pages-1)}{id}{add_tags}"
            self.booru_url = url
            res = requests.get(url, headers=self.headers)
            try:
                data = res.json()['posts']
            except Exception:
                data = []
            count = len(data)
            for post in data:
                if isinstance(post, dict):
                    temp_tags: List[str] = []
                    sublevels = ['general', 'artist', 'copyright', 'character', 'species']
                    tags = post.get('tags', {})
                    for sublevel in sublevels:
                        temp_tags.extend(tags.get(sublevel, []))
                    post['tags'] = ' '.join(temp_tags)
                    score = post.get('score', {}).get('total', 0)
                    post['score'] = score if isinstance(score, int) else 0
            if count <= max_pages * POST_AMOUNT:
                max_pages = count // POST_AMOUNT + 1
                if loop_msg:
                    loop_msg = False
                continue
            break
        return {'post': data}

    def get_post(self, add_tags: str, max_pages: int = 10, id: str = '') -> Dict[str, Any]:
        return self.get_data(add_tags, max_pages, "&id=" + id)


def generate_chaos(pos_tags: str, neg_tags: str, chaos_amount: float) -> Tuple[str, str]:
    rng = random.SystemRandom()
    chaos_list = [tag for tag in pos_tags.split(',') + neg_tags.split(',') if tag.strip() != '']
    chaos_list = list(set(chaos_list))
    rng.shuffle(chaos_list)
    len_list = round(len(chaos_list) * chaos_amount)
    pos_list = chaos_list[len_list:]
    pos_prompt = ','.join(pos_list)
    neg_list = chaos_list[:len_list]
    rng.shuffle(neg_list)
    neg_prompt = ','.join(neg_list)
    return pos_prompt, neg_prompt


def limit_prompt_tags(prompt: str, limit_tags: float | int, mode: str) -> str:
    clean_prompt = prompt.split(',')
    if mode == 'Limit':
        clean_prompt = clean_prompt[:int(len(clean_prompt) * float(limit_tags))]
    elif mode == 'Max':
        clean_prompt = clean_prompt[:int(limit_tags)]
    return ','.join(clean_prompt)


def _rating_token(booru: str, rating_label: str) -> str:
    mapping = RATINGS.get(booru, RATING_TYPES['none'])
    return mapping.get(rating_label, 'All')


def _sort_posts(posts: List[Dict[str, Any]], sorting_order: str) -> List[Dict[str, Any]]:
    for post in posts:
        if isinstance(post, dict):
            s = post.get('score')
            try:
                post['score'] = int(s) if s not in (None, '') else 0
            except Exception:
                post['score'] = 0
    if sorting_order == 'High Score':
        return sorted(posts, key=lambda k: (k.get('score') if isinstance(k, dict) else 0) or 0, reverse=True)
    if sorting_order == 'Low Score':
        return sorted(posts, key=lambda k: (k.get('score') if isinstance(k, dict) else 0) or 0)
    return posts


def _random_pick_index(sorting_order: str, count: int) -> int:
    if count <= 0:
        raise Exception("No posts found with those tags. Try lowering the pages or changing the tags.")
    if count > POST_AMOUNT:
        count = POST_AMOUNT
    if sorting_order in ('High Score', 'Low Score'):
        rng = random.SystemRandom()
        weights = list(range(count, 0, -1))
        total = sum(weights)
        probs = [w / total for w in weights]
        r = rng.random()
        acc = 0.0
        for i, p in enumerate(probs):
            acc += p
            if r <= acc:
                return i
        return count - 1
    else:
        return random.SystemRandom().randrange(count)


class RanbooruPrompt:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "booru": (['safebooru', 'rule34', 'danbooru', 'gelbooru', 'aibooru', 'xbooru', 'e621', 'konachan', 'yande.re'], {"default": "safebooru"}),
                "tags": ("STRING", {"default": ""}),
                "remove_bad_tags": ("BOOLEAN", {"default": True}),
                "remove_tags": ("STRING", {"default": ""}),
                "change_background": (['Don\'t Change', 'Add Background', 'Remove Background', 'Remove All'], {"default": "Don\'t Change"}),
                "change_color": (['Don\'t Change', 'Colored', 'Limited Palette', 'Monochrome'], {"default": "Don\'t Change"}),
                "shuffle_tags": ("BOOLEAN", {"default": True}),
                "change_dash": ("BOOLEAN", {"default": False}),
                "mix_prompt": ("BOOLEAN", {"default": False}),
                "mix_amount": ("INT", {"default": 2, "min": 2, "max": 10}),
                "mature_rating": (['All', 'Safe', 'Questionable', 'Explicit', 'g', 's', 'q', 'e'], {"default": "All"}),
                "sorting_order": (['Random', 'High Score', 'Low Score'], {"default": "Random"}),
                "limit_tags": ("FLOAT", {"default": 1.0, "min": 0.05, "max": 1.0, "step": 0.05}),
                "max_tags": ("INT", {"default": 100, "min": 1, "max": 100}),
                "use_search_txt": ("BOOLEAN", {"default": False}),
                "search_file": ("STRING", {"default": os.path.join(extension_root, 'user', 'search', 'tags_search.txt')}),
                "use_remove_txt": ("BOOLEAN", {"default": False}),
                "remove_file": ("STRING", {"default": os.path.join(extension_root, 'user', 'remove', 'tags_remove.txt')}),
                "use_cache": ("BOOLEAN", {"default": True}),
                "api_key": ("STRING", {"default": ""}),
                "user_id": ("STRING", {"default": ""}),
                "post_id": ("STRING", {"default": ""}),
                "max_pages": ("INT", {"default": 100, "min": 1, "max": 100}),
                "chaos_mode": (['None', 'Chaos', 'Less Chaos'], {"default": 'None'}),
                "chaos_amount": ("FLOAT", {"default": 0.5, "min": 0.1, "max": 1.0, "step": 0.05}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("positive", "negative")
    FUNCTION = "run"
    OUTPUT_NODE = False
    CATEGORY = "Ranbooru"

    def _build_booru(self, booru: str, fringe_benefits: bool, api_key: str, user_id: str):
        creds = credentials_manager.get_booru_credentials(booru)
        ak = api_key.strip() or creds.get('api_key', '')
        uid = user_id.strip() or creds.get('user_id', '')
        if booru == 'gelbooru':
            return Gelbooru(fringe_benefits, ak, uid)
        if booru == 'rule34':
            return Rule34(ak, uid)
        if booru == 'safebooru':
            return Safebooru()
        if booru == 'danbooru':
            return Danbooru()
        if booru == 'konachan':
            return Konachan()
        if booru == 'yande.re':
            return Yandere()
        if booru == 'aibooru':
            return AIBooru()
        if booru == 'xbooru':
            return XBooru()
        if booru == 'e621':
            return e621()
        return Gelbooru(fringe_benefits, ak, uid)

    def run(self, booru: str, tags: str, remove_bad_tags: bool, remove_tags: str,
            change_background: str, change_color: str, shuffle_tags: bool, change_dash: bool,
            mix_prompt: bool, mix_amount: int, mature_rating: str, sorting_order: str,
            limit_tags: float, max_tags: int, use_search_txt: bool, search_file: str,
            use_remove_txt: bool, remove_file: str, use_cache: bool, api_key: str, user_id: str,
            post_id: str, max_pages: int, chaos_mode: str, chaos_amount: float) -> Tuple[str, str]:

        if use_cache and HAS_REQUESTS_CACHE and not requests_cache.patcher.is_installed():
            requests_cache.install_cache('ranbooru_cache', backend='sqlite', expire_after=3600)
        elif not use_cache and HAS_REQUESTS_CACHE and requests_cache.patcher.is_installed():
            requests_cache.uninstall_cache()

        bad_tags: List[str] = []
        if remove_bad_tags:
            bad_tags = ['mixed-language_text', 'watermark', 'text', 'english_text', 'speech_bubble', 'signature', 'artist_name', 'censored', 'bar_censor', 'translation', 'twitter_username', 'twitter_logo', 'patreon_username', 'commentary_request', 'tagme', 'commentary', 'character_name', 'mosaic_censoring', 'instagram_username', 'text_focus', 'english_commentary', 'comic', 'translation_request', 'fake_text', 'translated', 'paid_reward_available', 'thought_bubble', 'multiple_views', 'silent_comic', 'out-of-frame_censoring', 'symbol-only_commentary', '3koma', '2koma', 'character_watermark', 'spoken_question_mark', 'japanese_text', 'spanish_text', 'language_text', 'fanbox_username', 'commission', 'original', 'ai_generated', 'stable_diffusion', 'tagme_(artist)', 'text_bubble', 'qr_code', 'chinese_commentary', 'korean_text', 'partial_commentary', 'chinese_text', 'copyright_request', 'heart_censor', 'censored_nipples', 'page_number', 'scan', 'fake_magazine_cover', 'korean_commentary']

        if remove_tags:
            if ',' in remove_tags:
                bad_tags.extend([t for t in remove_tags.split(',') if t])
            else:
                bad_tags.append(remove_tags)

        if use_remove_txt and os.path.exists(remove_file):
            try:
                with open(remove_file, 'r', encoding='utf-8') as f:
                    bad_tags.extend(f.read().split(','))
            except Exception:
                pass

        prompt_addition = ''
        if change_background == 'Add Background':
            prompt_addition = 'detailed_background,' + random.choice(["outdoors", "indoors"]) 
        elif change_background == 'Remove Background':
            prompt_addition = 'plain_background,simple_background,' + random.choice(COLORED_BG)
            bad_tags.extend(ADD_BG)
        elif change_background == 'Remove All':
            bad_tags.extend(COLORED_BG + ADD_BG)

        if change_color == 'Colored':
            bad_tags.extend(BW_BG)
        elif change_color == 'Limited Palette':
            prompt_addition = f"{prompt_addition},{'(limited_palette:1.3)'}" if prompt_addition else '(limited_palette:1.3)'
        elif change_color == 'Monochrome':
            prompt_addition = f"{prompt_addition},{','.join(BW_BG)}" if prompt_addition else ','.join(BW_BG)

        if use_search_txt and os.path.exists(search_file):
            try:
                with open(search_file, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f.read().replace(' ', '').splitlines() if line.strip()]
                if lines:
                    selected = random.SystemRandom().choice(lines)
                    tags = f"{tags},{selected}" if tags else selected
            except Exception:
                pass

        add_tags = '&tags=-animated'
        if tags:
            add_tags += '+' + tags.replace(',', '+')
            if mature_rating != 'All':
                token = _rating_token(booru, mature_rating)
                if token != 'All':
                    add_tags += f"+rating:{token}"

        api = self._build_booru(booru, fringe_benefits=True, api_key=api_key, user_id=user_id)
        data = api.get_post(add_tags, max_pages, post_id) if post_id else api.get_data(add_tags, max_pages)
        posts = data.get('post', []) if isinstance(data, dict) else []
        if not isinstance(posts, list):
            posts = []

        if len(posts) == 0 and booru == 'rule34' and add_tags.startswith('&tags=-animated'):
            ft = '&tags='
            if tags:
                ft += tags.replace(',', '+')
            if mature_rating != 'All':
                token = _rating_token(booru, mature_rating)
                if token != 'All':
                    ft += f"+rating:{token}"
            data = api.get_data(ft, max_pages)
            posts = data.get('post', []) if isinstance(data, dict) else []

        if len(posts) == 0:
            return ('未找到符合条件的帖子', '')

        posts = _sort_posts(posts, sorting_order)
        rn = _random_pick_index(sorting_order, len(posts))

        rng = random.SystemRandom()
        rp = posts[rn]
        if mix_prompt:
            temp_tags: List[str] = []
            mt = 0
            for _ in range(0, int(mix_amount)):
                rm = _random_pick_index(sorting_order, len(posts))
                tmp = posts[rm].get('tags', '')
                temp_tags.extend(tmp.split(' '))
                mt = max(mt, len(tmp.split(' ')))
            temp_tags = list(set(temp_tags))
            mt = min(max(len(temp_tags), 20), mt)
            rp = dict(rp)
            rp['tags'] = ' '.join(rng.sample(temp_tags, mt))

        clean_tags = rp.get('tags', '').replace('(', r'\(').replace(')', r'\)')
        temp_tags = rng.sample(clean_tags.split(' '), len(clean_tags.split(' '))) if shuffle_tags else clean_tags.split(' ')
        pos_prompt = ','.join([t for t in temp_tags if t.strip() not in bad_tags])
        for bt in bad_tags:
            if '*' in bt:
                pos_prompt = ','.join([t for t in pos_prompt.split(',') if bt.replace('*', '') not in t])
        if change_dash:
            pos_prompt = pos_prompt.replace('_', ' ')
        if limit_tags < 1:
            pos_prompt = limit_prompt_tags(pos_prompt, limit_tags, 'Limit')
        if max_tags > 0:
            pos_prompt = limit_prompt_tags(pos_prompt, max_tags, 'Max')
        final_positive = f"{prompt_addition},{pos_prompt}" if prompt_addition else pos_prompt

        final_negative = ''
        if chaos_mode in ['Chaos', 'Less Chaos']:
            base_neg = '' if chaos_mode == 'Less Chaos' else ''
            final_positive, final_negative = generate_chaos(final_positive, base_neg, chaos_amount)

        return (final_positive, final_negative)


NODE_CLASS_MAPPINGS = {
    "RanbooruPrompt": RanbooruPrompt,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RanbooruPrompt": "Ranbooru Prompt",
}