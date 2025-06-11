import re

HEADERS = {
    'Cache-Control': 'max-age=0',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0',
    'Accept-Language': 'uk-UA,uk;q=0.8,en-US;q=0.5,en;q=0.3',
    'Connection': 'keep-alive',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
              'application/signed-exchange;v=b3;q=0.9'
}

VALID_STATUSES = [101, 200, 204, 301, 302, 307, 308, 401, 403, 500, 501, 502]
URL_IGNORE_EXT_REGEX = re.compile(
    '\.jpg$|\.jpeg$|\.svg$|\.gif$|\.png$|\.zip$|\.pdf$|\.exe$|\.dmg$|\.txt$|\.xlsx$|\.xls$|\.doc$'
    '|\.eot$|\.ttf$|\.woff$|\.woff2$|\.docx$|\.m4v$|\.pptx$|\.ppt$|\.mp4$|\.avi$|\.mp3$|\.css$|\.min\.js$|jquery\.js$',
    re.IGNORECASE)

SOCIAL_MEDIA = ["facebook", "twitter", "linkedin", "youtube", "google", "intercom", "atlassian", "instagram", "github",
                "letgo", "yahoo", "microsoft"]
