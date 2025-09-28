import imaplib, ssl, email
from email.header import decode_header
import re, time, random

class Mail:
    def __init__(self, mailAddr):
        self.IMAP_HOST = "imap.gmail.com"
        self.IMAP_PORT = 993
        self.EMAIL = ""
        self.PASSWORD= ""
        self.MAX_RESULTS = 20 # 只取最新 N 封，避免一次取太多
        self.RECIPIENT = mailAddr

    def decode_subject(self, raw):
        parts = decode_header(raw or "")
        out = []
        for bytes_or_str, enc in parts:
            if isinstance(bytes_or_str, bytes):
                out.append(bytes_or_str.decode(enc or "utf-8", errors="ignore"))
            else:
                out.append(bytes_or_str)
        return "".join(out)

    def extract_bodies(self, msg):
        """返回 (text/plain, text/html)，若没有则为空字符串"""
        body_text, body_html = "", ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_maintype() == "multipart":
                    continue
                if (part.get("Content-Disposition") or "").lower().strip().startswith("attachment"):
                    continue  # 跳过附件
                ctype = part.get_content_type()
                charset = part.get_content_charset() or "utf-8"
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                try:
                    text = payload.decode(charset, errors="ignore")
                except LookupError:
                    text = payload.decode("utf-8", errors="ignore")
                if ctype == "text/plain":
                    body_text += text
                elif ctype == "text/html":
                    body_html += text
        else:
            ctype = msg.get_content_type()
            charset = msg.get_content_charset() or "utf-8"
            payload = msg.get_payload(decode=True)
            if payload:
                try:
                    text = payload.decode(charset, errors="ignore")
                except LookupError:
                    text = payload.decode("utf-8", errors="ignore")
                if ctype == "text/plain":
                    body_text = text
                elif ctype == "text/html":
                    body_html = text
        return body_text.strip(), body_html.strip()
    
    def connect(self):
        ctx = ssl.create_default_context()
        M = imaplib.IMAP4_SSL(self.IMAP_HOST, self.IMAP_PORT, ssl_context=ctx)
        M.login(self.EMAIL, self.PASSWORD)
        M.select("INBOX", readonly=True)
        return M
    
    def search_uids(self, M: imaplib.IMAP4_SSL) -> list[bytes]:
        typ, data = M.uid("search", None, "OR", "TO", self.RECIPIENT, "CC", self.RECIPIENT)

        if typ!= "OK":
            return []
        
        ids = data[0].split()
        if not ids:
            return []
        return ids[-self.MAX_RESULTS:]
    
    def fetch(self, M: imaplib.IMAP4_SSL, uid: bytes):
        typ, msg_data = M.uid("fetch", uid, "(BODY.PEEK[])")
        if typ != "OK" or not msg_data or not msg_data[0]:
            return False
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        text, html = self.extract_bodies(msg)

        return text or html
    
    def handle(self, text):
        pattern = r"https?://[^\s]+"
        url = re.search(pattern, text)
        if url:
            return url.group()
    
    def getRegisterLink(self):
        M = None

        try:
            M = self.connect()
            i = 1
            while True:
                print(f"第 {i} 次查询邮件中")
                uids = self.search_uids(M)
                if uids and uids[0]:
                    print(f"查询邮件成功，正在处理")
                    text = self.fetch(M, uids[0])
                    registerURL = self.handle(text)
                    return registerURL
                
                time.sleep(random.randint(3000, 5000) / 1000)
                i += 1
                M.noop()
        finally:
            if M is not None:
                M.logout()
