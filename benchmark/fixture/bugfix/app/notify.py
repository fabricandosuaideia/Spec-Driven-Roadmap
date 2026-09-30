"""Customer notifications."""
import unicodedata


def email_subject(text):
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def sms_text(text):
    return text
