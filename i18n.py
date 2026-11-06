"""Local UI translations. User text and form values are never translated."""
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import json
import re

CATALOG=json.loads(Path(__file__).with_name('translations.json').read_text(encoding='utf-8'))
PATTERN=re.compile('|'.join(re.escape(key) for key in sorted(CATALOG,key=len,reverse=True)))


def translate(text,language):
    if language=='zh-Hant':return text
    index=0 if language=='zh-Hans' else 1
    # One pass avoids translating a replacement a second time.
    return PATTERN.sub(lambda m:CATALOG[m.group()][index],text)


class Localizer(HTMLParser):
    def __init__(self,language):
        super().__init__(convert_charrefs=False)
        self.language=language
        self.output=[]
        self.stack=[]

    def handle_starttag(self,tag,attrs):
        skip=any(v for _,v in self.stack) or tag in ('script','style','textarea') or any(k=='data-user' for k,v in attrs)
        if tag not in ('input','meta','link','br','hr','img'):
            self.stack.append((tag,skip))
        result=[]
        for key,value in attrs:
            if tag=='html' and key=='lang':value=self.language
            if value is not None and key in ('aria-label','placeholder') and not skip:
                value=translate(value,self.language)
            result.append(key if value is None else key+'="'+escape(value,quote=True)+'"')
        self.output.append('<'+tag+(' '+' '.join(result) if result else '')+'>')

    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if self.stack and self.stack[-1][0]==tag:self.stack.pop()
        self.output[-1]=self.output[-1][:-1]+'/>'

    def handle_endtag(self,tag):
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:
                del self.stack[i:]
                break
        self.output.append('</'+tag+'>')

    def handle_data(self,text):
        if not any(v for _,v in self.stack):
            text=translate(text,self.language)
            if self.language=='en':
                text=re.sub(r'(\d+) 年 (\d+) 月',r'\1 / \2',text)
                text=re.sub(r'(\d+) 月 (\d+) 日，',r'\1 / \2, ',text)
        self.output.append(text)

    def handle_entityref(self,name):self.output.append('&'+name+';')
    def handle_charref(self,name):self.output.append('&#'+name+';')
    def handle_decl(self,decl):self.output.append('<!'+decl+'>')


def localize_html(html,language):
    if language=='zh-Hant':return html
    parser=Localizer(language)
    parser.feed(html)
    return ''.join(parser.output)


def client_messages(language):
    return {key:translate(key,language) for key in CATALOG}
