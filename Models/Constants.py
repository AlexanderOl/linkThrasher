import re

VALID_STATUSES = [101, 200, 204, 301, 302, 307, 308, 401, 403, 405, 500]
URL_IGNORE_EXT_REGEX = re.compile(
    '\.jpg$|\.jpeg$|\.gif$|\.png$|\.js$|\.zip$|\.pdf$|\.ashx$|\.exe$|\.dmg$|\.txt$|\.xlsx$|\.xls$|\.doc$'
    '|\.docx$|\.m4v$|\.pptx$|\.ppt$|\.mp4$|\.avi$|\.mp3$',
    re.IGNORECASE)

SOCIAL_MEDIA = ["facebook", "twitter", "linkedin", "youtube", "google", "intercom", "atlassian", "instagram", "github",
                "letgo", "yahoo", "microsoft"]
