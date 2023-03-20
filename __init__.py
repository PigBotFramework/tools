from pbf import PBF
from utils.RegCmd import RegCmd
import sys, os, hmac, html, pymysql, requests, json, time, re, random, hashlib, traceback, datetime, pytz
from bilibili_api import user, sync
from urllib import parse
from PbfStruct import Struct
from utils.cqcode import CQCode
import utils.nsfw.classify_nsfw as nsfw
try:
    import nest_asyncio
    nest_asyncio.apply()
except Exception as e:
    pass

_name = "实用功具"
_version = "1.0.1"
_description = "超多实用工具，包含近一半的指令"
_author = "xzyStudio"
_cost = 0.00

#兽音译者，一种将“呜嗷啊~”四个字符，通过特殊算法，将明文进行重新组合的加密算法。一种新的咆哮体加密算法。还可以将四个字符任意换成其它的字符，进行加密。
#另，可下载油猴插件Google selected text translator，https://greasyfork.org/en/scripts/36842-google-select-text-translator
#该插件经设置后，不仅可以划词翻译兽音密文，也可生成兽音密文
class HowlingAnimalsTranslator:

    __animalVoice="嗷呜啊~"

    def __init__(self,newAnimalVoice=None):
        self.setAnimalVoice(newAnimalVoice)

    def convert(self,txt=""):
        txt=txt.strip()
        if(txt.__len__()<1):
            return ""
        result=self.__animalVoice[3]+self.__animalVoice[1]+self.__animalVoice[0]
        offset=0
        for t in txt:
            c=ord(t)
            b=12
            while(b>=0):
                hex=(c>>b)+offset&15
                offset+=1
                result+=self.__animalVoice[int(hex>>2)]
                result+=self.__animalVoice[int(hex&3)]
                b-=4
        result+=self.__animalVoice[2]
        return result

    def deConvert(self,txt):
        txt=txt.strip()
        if(not self.identify(txt)):
            return "Incorrect format!"
        result=""
        i=3
        offset=0
        while(i<txt.__len__()-1):
            c=0
            b=i+8
            while(i<b):
                n1=self.__animalVoice.index(txt[i])
                i+=1
                n2=self.__animalVoice.index(txt[i])
                c=c<<4|((n1<<2|n2)+offset)&15
                if(offset==0):
                    offset=0x10000*0x10000-1
                else:
                    offset-=1
                i+=1
            result+=chr(c)
        return result

    def identify(self,txt):
        if(txt):
            txt=txt.strip()
            if(txt.__len__()>11):
                if(txt[0]==self.__animalVoice[3] and txt[1]==self.__animalVoice[1] and txt[2]==self.__animalVoice[0] and txt[-1]==self.__animalVoice[2] and ((txt.__len__()-4)%8)==0):
                    for t in txt:
                        if(not self.__animalVoice.__contains__(t)):
                            return False
                    return True
        return False

    def setAnimalVoice(self,voiceTxt):
        if(voiceTxt):
            voiceTxt=voiceTxt.strip()
            if(voiceTxt.__len__()==4):
                self.__animalVoice=voiceTxt
                return True
        return False

    def getAnimalVoice(self):
        return self.__animalVoice

def getDynamic(uid):
    print("getDynamic: ", uid)

    u = user.User(int(uid))
    dynamics = []
    page = sync(u.get_dynamics())
    if 'cards' in page:
        dynamics.extend(page['cards'])
    dynamic_id = max(dynamics[0].get("desc").get("dynamic_id"), dynamics[-1].get("desc").get("dynamic_id"))
    return dynamic_id

async def screenshotDynamic(dynamic_id):
    from playwright.async_api import async_playwright
    url = f"https://t.bilibili.com/{dynamic_id}"
    filename = "{}.png".format(time.time())
    p = await async_playwright().start()
    browser = await p.chromium.launch()
    context = await browser.new_context(
        viewport={"width": 2560, "height": 1080},
        device_scale_factor=2,
    )
    await context.add_cookies(
        [
            {
                "name": "hit-dyn-v2",
                "value": "1",
                "domain": ".bilibili.com",
                "path": "/",
            }
        ]
    )
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="networkidle", timeout=10000)
        # 动态被删除或者进审核了
        if page.url == "https://www.bilibili.com/404":
            return None
        card = await page.query_selector(".card")
        assert card
        clip = await card.bounding_box()
        assert clip
        bar = await page.query_selector(".bili-dyn-action__icon")
        assert bar
        bar_bound = await bar.bounding_box()
        assert bar_bound
        clip["height"] = bar_bound["y"] - clip["y"]
        await page.screenshot(clip=clip, full_page=True, path='./resources/createimg/'+str(filename))
    except Exception:
        await page.screenshot(full_page=True, path='./resources/createimg/'+str(filename))
    finally:
        await context.close()
    return filename

class tools(PBF):
    def __enter__(self):
        from utils import scheduler
        scheduler.add_job(BilibiliSub, 'interval', seconds=40, id="BilibiliSub", replace_existing=True)
        '''
        for i in self.mysql.selectx("SELECT * FROM `botSettings`"):
            if i.get('sche') != 0 and i.get('sche') < 600:
                scheduler.add_job(scheNotice, 'interval', seconds=i.get('sche'), id=f"sche{i.get('qn')}", replace_existing=True, kwargs={"qn":i.get("qn"),"content":i.get('scheContent'),"uuid":i.get("uuid")})
        '''

        return [
            RegCmd(
                name = "翻译 ",
                usage = "翻译 <目标语言>",
                permission = "anyone",
                function = "tools@trans",
                description = "翻译到任何语言（谷歌翻译）",
                mode = "实用功能",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "查 ",
                usage = "查 <@对方>",
                permission = "owner",
                function = "tools@chaQQ",
                description = "查询QQ绑定",
                mode = "防护系统",
                hidden = 1,
                type = "command"
            ),
            RegCmd(
                name = "兽语加密 ",
                usage = "兽语加密 <内容>",
                permission = "anyone",
                function = "tools@encode_shou_u",
                description = "兽语加密",
                mode = "兽言兽语",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "兽语解密 ",
                usage = "兽语解密 <内容>",
                permission = "anyone",
                function = "tools@decode_shou_u",
                description = "兽语解密",
                mode = "兽言兽语",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "戳一戳 ",
                usage = "戳一戳 <@对方QQ>",
                permission = "owner",
                function = "tools@chuo",
                description = "让机器人戳一戳",
                mode = "只因器人",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "群发 ",
                usage = "群发 <群发内容>",
                permission = "owner",
                function = "tools@qunfa",
                description = "给机器人加入的群发消息",
                mode = "公告系统",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "友发 ",
                usage = "友发 <要给每个好友发的消息内容>",
                permission = "ro",
                function = "tools@haoyoufa",
                description = "给机器人好友发送消息",
                mode = "公告系统",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "说 ",
                usage = "说 <消息内容>",
                permission = "owner",
                function = "tools@echo",
                description = "让机器人说",
                mode = "只因器人",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "cqcode ",
                usage = "cqcode <CQ的值>[ <附加参数(键值对)> ...]",
                permission = "owner",
                function = "tools@cqcode",
                description = "发送自定义CQ码",
                mode = "只因器人",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "md5 ",
                usage = "md5 <要加密的内容>",
                permission = "anyone",
                function = "tools@md5",
                description = "MD5加密",
                mode = "实用功能",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "转语音 ",
                usage = "转语音 <要转语音的内容>",
                permission = "owner",
                function = "tools@zhuan",
                description = "将文字转为语音",
                mode = "实用功能",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "mysql查询 ",
                usage = "mysql查询 <sql语句>",
                permission = "xzy",
                function = "tools@mysqlselect",
                description = "对php10数据库执行sql语句",
                mode = "只因器人",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "mysql执行 ",
                usage = "mysql执行 <sql语句>",
                permission = "xzy",
                function = "tools@mysqlgo",
                description = "对php10数据库进行查询操作",
                mode = "只因器人",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "运势",
                usage = "运势",
                permission = "anyone",
                function = "tools@yunshi",
                description = "今天运势怎么样呢awa",
                mode = "装神弄鬼",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "逐字汉译英 ",
                usage = "逐字汉译英 <要翻译的内容>",
                permission = "anyone",
                function = "tools@twbw",
                description = "逐字逐句地翻译",
                mode = "实用功能",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "网页截图 ",
                usage = "网页截图 <地址>",
                permission = "ao",
                function = "tools@getWP",
                description = "给网页截图",
                mode = "网页截图",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "百度搜索 ",
                usage = "百度搜索 <关键词>",
                permission = "anyone",
                function = "tools@baiduSearch",
                description = "使用百度搜索，发送结果截图",
                mode = "搜索系统",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "B站搜索 ",
                usage = "B站搜索 <关键词>",
                permission = "anyone",
                function = "tools@biliSearch",
                description = "使用B站搜索，发送结果截图",
                mode = "搜索系统",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "必应搜索 ",
                usage = "必应搜索 <关键词>",
                permission = "anyone",
                function = "tools@bingSearch",
                description = "使用必应搜索，发送结果截图",
                mode = "搜索系统",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "谷歌搜索 ",
                usage = "谷歌搜索 <关键词>",
                permission = "anyone",
                function = "tools@googleSearch",
                description = "使用谷歌搜索，发送结果截图",
                mode = "搜索系统",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "生成拦截 ",
                usage = "生成拦截 <要生成的网址>",
                permission = "anyone",
                function = "tools@shengchenghonglian",
                description = "生成qq拦截的页面",
                mode = "网页截图",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "怼 ",
                usage = "怼 <@要怼的人> <次数> <间隔时间>",
                permission = "owner",
                function = "tools@dui",
                description = "让机器人怼人",
                mode = "防护系统",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "新手教程",
                usage = "新手教程",
                permission = "anyone",
                function = "tools@xinshou",
                description = "发送新手教程",
                mode = "新手入门",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "获取头像 ",
                usage = "获取头像 <@要获取的人>",
                permission = "anyone",
                function = "tools@getHeadImage",
                description = "获取某人的头像！",
                mode = "实用功能",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "关机",
                usage = "关机",
                permission = "ao",
                function = "tools@TurnOffBot",
                description = "关闭机器人",
                mode = "群聊管理",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "BOTQG",
                usage = "让机器人退群",
                permission = "ro",
                function = "tools@QuiteGroup",
                description = "让机器人退群",
                mode = "防护系统",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "今日人品",
                usage = "今日人品",
                permission = "anyone",
                function = "tools@renpin",
                description = "来看看今天人品咋样吧qwq",
                mode = "装神弄鬼",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "插件列表",
                usage = "插件列表",
                permission = "anyone",
                function = "tools@listPlugins",
                description = "列出当前机器人本地的插件",
                mode = "只因器人",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "艾特全体",
                usage = "艾特全体",
                permission = "admin",
                function = "tools@atAll",
                description = "艾特全体成员",
                mode = "实用功能",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "获取动态 ",
                usage = "获取动态 <B站ID>",
                permission = "anyone",
                function = "tools@dynamic",
                description = "获取动态",
                mode = "B 站爬虫",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "B站订阅 ",
                usage = "B站订阅 <B站ID>",
                permission = "ao",
                function = "tools@addBiliSub",
                description = "订阅UP猪的动态推送！",
                mode = "B 站爬虫",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "B站取关 ",
                usage = "B站取关 <B站ID>",
                permission = "ao",
                function = "tools@delBiliSub",
                description = "取关动态推送！",
                mode = "B 站爬虫",
                hidden = 0,
                type = "command"
            ),
            RegCmd(
                name = "B站关注列表",
                usage = "B站关注列表",
                permission = "anyone",
                function = "tools@listBiliSub",
                description = "查看本群关注的UP猪们",
                mode = "B 站爬虫",
                hidden = 0,
                type = "command"
            )
        ]

    def dynamic(self, echo=True):
        try:
            if echo:
                self.send("获取B站动态: {}".format(self.data.message))
            dynamic_id = getDynamic(self.data.message)
            filename = sync(screenshotDynamic(dynamic_id))
            if filename:
                self.send("[CQ:image,cache=0,file=https://pbfresources.xzynb.top/createimg/"+str(filename)+"]")
            else:
                raise ValueError("Cannot found user or dynamic")
        except Exception as e:
            self.send("emmm...找不到该用户或动态\n错误：{}".format(e))
    
    def atAll(self):
        dataa = self.client.CallApi('get_group_member_list', {"group_id":self.data.se.get("group_id")}).get("data")
        message = ""
        for i in dataa:
            message += "[CQ:at,qq={}]".format(i.get("user_id"))
        self.send(message)
    
    def encode_shou_u(self):
        shou = HowlingAnimalsTranslator()
        self.send(shou.convert(self.data.message))
        
    def decode_shou_u(self):
        shou = HowlingAnimalsTranslator()
        self.send(shou.deConvert(self.data.message))
    
    def chaQQ(self):
        try:
            userid = self.data.message
            if 'at' in userid:
                userid = CQCode(self.data.message).get("qq")[0]
            data = requests.get('https://api.xywlapi.cc/qqapi?qq={}'.format(userid)).json()
            if data.get('status') != 200:
                return self.send('[CQ:face,id=171] 查询失败！')
            message = '[CQ:face,id=171] 用户QQ：{}\n[CQ:face,id=171] 手机号：{}\n[CQ:face,id=171] 地区：{}'.format(data.get('qq'), data.get('phone'), data.get('phonediqu'))
            self.send(message)
        except Exception as e:
            self.logger.warning(e, "tools.chaQQ")
    
    def listPlugins(self):
        message = '{0}-插件列表'.format(self.data.botSettings.get('name'))
        for i in self.pluginsList:
            message += '\n[CQ:face,id=54] 插件名称：'+str(i)
        # message += '\n\n所有插件均原创插件'
        self.send(message)
    
    def dui(self):
        uid = self.data.se.get('user_id')
        gid = self.data.se.get('group_id')
        message = self.data.message
        
        message1 = message.split(' ')
        userid = CQCode(message1[0]).get("qq")[0]
        cishu = int(message1[1])
        jiangetime = int(message1[2])
        while cishu > 0:
            dataa = requests.get(url=self.data.botSettings.get('duiapi'))
            dataa.enconding = "utf-8"
            self.send('[CQ:at,qq='+str(userid)+']'+str(dataa.text))
            time.sleep(jiangetime+random.uniform(0, 2))
            
            cishu -= 1
    
    
    def whoonline(self):
        uid = self.data.se.get('user_id')
        gid = self.data.se.get('group_id')
        
        dataa = self.client.CallApi('get_online_clients', {})
        self.send(dataa)
    
    def chuo(self):
        uid = self.data.se.get('user_id')
        gid = self.data.se.get('group_id')
        message = self.data.message
        
        message1 = CQCode(message).get("qq")[0]
        self.send('[CQ:poke,qq='+message1+']')
        
    def zhuan(self):
        uid = self.data.se.get('user_id')
        gid = self.data.se.get('group_id')
        message = self.data.message
        
        self.send("[CQ:tts,text="+str(message)+"]")
            
    def echo(self):
        self.send(self.data.message)
        # self.send("raise error")
        # raise UnkownError("Sussy Baka")
    
    def haoyoufa(self):
        uid = self.data.se.get('user_id')
        gid = self.data.se.get('group_id')
        message = self.data.message
        
        self.send("开始发送...")
        dataa = self.client.CallApi('get_friend_list', {})
        sum = 0
        for i in dataa.get('data'):
            if i.get('user_id') == 66600000:
                continue
            self.client.msg(message).custom(i.get("user_id"))
            self.logger.warning('好友 '+str(i.get('nickname'))+' 发送完毕')
            sum += 1
            time.sleep(1+random.randint(0,10))
        self.send('发送完毕，总好友数：'+str(sum))
    
    def qunfa(self):
        uid = self.data.se.get('user_id')
        gid = self.data.se.get('group_id')
        message = self.data.message
        
        # 同步公告到数据库
        self.send("同步公告...")
        formatmsg = message.replace('\n', '<br>')
        postdata = {"content":formatmsg}
        requests.post('https://pbf.xzynb.top/savenotice', data=postdata)
        
        self.send("开始发送...")
        try:
            dataa = self.client.CallApi('get_group_list', {})
            sum = 0
            for i in dataa.get('data'):
                self.client.msg(message).custom(uid, i.get('group_id'))
                self.logger.warning('群聊 '+str(i.get('group_name'))+' 发送完毕', '群发消息公告')
                time.sleep(1+random.randint(0,10))
                sum += 1
            self.send('发送完毕，总群聊数：'+str(sum))
        except Exception as e:
            self.send(e)
    
    def cqcode(self):
        uid = self.data.se.get('user_id')
        gid = self.data.se.get('group_id')
        message = self.data.message
        
        print('init cqcode')
        message1 = message.split(' ')
        message = '[CQ:'+str(message1[0])
        for i in message1:
            if '=' in i:
                message += ','+i
            else:
                continue
        message += ']'
        self.send(message)
    
    def md5(self):
        message = self.data.message
        self.send('MD5加密结果：'+str(hashlib.md5(message.encode(encoding='UTF-8')).hexdigest()))
    
    def mysqlselect(self):
        message = self.data.message
        self.send(self.mysql.selectx(message))
        
    def mysqlgo(self):
        message = self.data.message
        self.mysql.commonx(message)
        self.send('[CQ:face,id=54] 执行完毕！')
    
    def twbw(self):
        uid = self.data.se.get('user_id')
        gid = self.data.se.get('group_id')
        message = self.data.message
        
        self.send('玩命翻译中...')
        message1 = '翻译结果：'
        for i in message:
            message1 += self.utils.translator(i)+' '
        self.send(message1)
    
    def biliSearch(self):
        uid = self.data.se.get('user_id')
        gid = self.data.se.get('group_id')
        message = self.data.message
        
        self.send('[CQ:face,id=189] 开始搜索...')
        message = message.lstrip().rstrip().replace(' ', '%20')
        
        self.data.message = 'https://search.bilibili.com/all?keyword='+str(message)+' 1 biliSearch.png'
        self.getWP(echo=False) # , add_script="document.getElementsById('bili-header-container').forEach(v=>v.remove());"
        
    def bingSearch(self):
        uid = self.data.se.get('user_id')
        gid = self.data.se.get('group_id')
        message = self.data.message
        
        self.send('[CQ:face,id=189] 开始搜索...')
        message = message.lstrip().rstrip().replace(' ', '%20')
        
        self.data.message = 'https://cn.bing.com/search?q='+str(message)+' 1 bing.png'
        self.getWP(echo=False)
        
    def googleSearch(self):
        uid = self.data.se.get('user_id')
        gid = self.data.se.get('group_id')
        message = self.data.message
        
        self.send('[CQ:face,id=189] 开始搜索...')
        message = message.lstrip().rstrip().replace(' ', '%20')
        
        self.data.message = 'https://www.google.com/search?q='+str(message)+' 1 google.png'
        self.getWP(echo=False)

    def baiduSearch(self):
        uid = self.data.se.get('user_id')
        gid = self.data.se.get('group_id')
        message = self.data.message
        
        self.send('[CQ:face,id=189] 开始搜索...')
        message = message.lstrip().rstrip().replace(' ', '%20')
        
        self.data.message = 'https://baidu.com/s?word='+str(message)+' 1 baiduSearch.png'
        self.getWP(echo=False)
    
    def getWP(self, echo=True, length=0, add_script=None):
        async def getScreen(filename, waittime=1, echo=True, add_script=None):
            from playwright.async_api import async_playwright
            p = await async_playwright().start()
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url)
            if add_script != None:
                await page.evaluate(add_script)
            if echo:
                self.send("网页还没加载完，再等{}秒看看".format(waittime))
            time.sleep(waittime)
            await page.screenshot(path='./resources/createimg/'+str(filename), full_page=True)
            await browser.close()
        
        uid = self.data.se.get('user_id')
        gid = self.data.se.get('group_id')
        message = self.data.message
        
        #  or int(self.client.CallApi('check_url_safely', {'url':message}, timeout=20).get('data').get('level')) == 3
        try:
            if ('pornhub' in message) or ('pronhub' in message) or ('pixiv' in message):
                if echo:
                    self.send('不可以涩涩哦~')
            else:
                if message[0:7] == "http://" or message[0:8] == "https://":
                    if echo:
                        self.send('玩命截图中...')
                    
                    waittime = 1
                    url = message
                    if ' ' in message:
                        message1 = message.split(' ')
                        url = message1[0]
                        waittime = int(message1[1])
                        filename = message[2]
                    else:
                        filename = parse.urlparse(str(message))[1] + '.png'
                    
                    sync(getScreen(filename, waittime, echo, add_script))
                    
                    if echo:
                        try:
                            self.send("为防止发送违禁图片，开始nsfw测试")
                            nsfwPer = nsfw.main("./resources/createimg/{0}".format(filename))["nsfw"]
                            if nsfwPer >= 0.8:
                                self.send("nsfw指数大于等于0.8，图片涉黄")
                            else:
                                self.send("[CQ:image,cache=0,file=https://pbfresources.xzynb.top/createimg/"+str(filename)+"] 以上图片内容与本机器人无关，本机器人只提供截图服务！")
                        except Exception:
                            self.send("[CQ:image,cache=0,file=https://pbfresources.xzynb.top/createimg/"+str(filename)+"] 以上图片内容与本机器人无关，本机器人只提供截图服务！")
                    else:
                        self.send("[CQ:image,cache=0,file=https://pbfresources.xzynb.top/createimg/"+str(filename)+"]")
                else:
                    self.send('[CQ:face,id=151] 请使用正确的协议头！')
        except Exception as e:
            self.send('截获错误，请检查网站网址是否正确，是否可以访问\n错误信息：{}'.format(traceback.format_exc()))
    
    def trans(self):
        message = self.utils.translator(self.data.message.replace(self.data.args[1], '').strip(), to_lang=self.data.args[1], from_lang=None)
        # 此处如果不设置from_lang为None则to_lang为zh时就不会翻译
        self.send('[CQ:reply,id={}] {}'.format(self.data.se.get('message_id'), message))
    
    def renpin(self):
        uid = self.data.se.get('user_id')
        gid = self.data.se.get('group_id')
        
        rnd = random.Random()
        rnd.seed(int(datetime.date.today().strftime("%y%m%d")) + int(uid))
        lucknum = rnd.randint(1,100)
        self.send('[CQ:at,qq='+str(uid)+'] 您的今日人品为：'+str(lucknum))
    
    def QuiteGroup(self):
        uid = self.data.se.get('user_id')
        gid = self.data.se.get('group_id')
        
        self.send('机器人即将退群！')
        data = self.client.CallApi('set_group_leave', {"group_id":gid})
    
    def TurnOffBot(self):
        uid = self.data.se.get('user_id')
        gid = self.data.se.get('group_id')
        
        self.mysql.commonx('UPDATE `botSettings` SET `power`=0 WHERE `qn`=%s', (gid))
        self.send('用户 [CQ:at,qq='+str(uid)+'] 关闭了机器人\n再见了呜呜呜，希望机器人的下一次开机~')
    
    def getHeadImage(self):
        uid = self.data.se.get('user_id')
        gid = self.data.se.get('group_id')
        message = self.data.message
        
        message1 = CQCode(message).get("qq")[0]
        data = requests.get(self.data.botSettings.get('headImageApi').format(message1))
        dataa = data.json()
        imgurl = dataa.get('data').get('imgurl2')
        name = str(dataa.get('data').get('name'))
        
        self.send('用户 '+message+' 的头像为\n[CQ:image,cache=0,url='+imgurl+',file='+imgurl+']')
    
    def xinshou(self):
        uid = self.data.se.get('user_id')
        gid = self.data.se.get('group_id')
        
        message = '[CQ:face,id=189] 新手教学，参阅：https://pbfuserdoc.xzynb.top 使用手册'
        self.send(message)
        
    def yunshi(self):
        uid = self.data.se.get('user_id')
        gid = self.data.se.get('group_id')
        cid = self.data.se.get('channel_id')
        
        if cid != None:
            strr = 'cid'
            sqlstr = '`cid`=%s'
        else:
            strr = 'qn'
            sqlstr = '`qn`=%s'
        ob = self.data.userInfo
        
        if ob==None:
            return self.send('请先发送“注册”，注册后再测运势')
        
        if ob.get('zong') == '' or ob.get('shiye') == 0 or ob.get('taohua') == 0 or ob.get('cai') == 0:
            self.send('[CQ:face,id=151] 祈祷中...')
            shiye = random.randint(1, 100)
            taohua = random.randint(1, 100)
            cai = random.randint(1, 100)
            zong = random.randint(0, 4)
            zongarr = ['大凶','小凶','凶带吉','吉带凶','小吉','大吉']
            zongstr = zongarr[zong]
            try:
                sql = 'UPDATE `botCoin` SET `zong`=%s,`shiye`=%s,`taohua`=%s,`cai`=%s WHERE {}'.format(sqlstr)
                self.mysql.commonx(sql, (zongstr, shiye, taohua, cai, uid))
                
                cache.refreshFromSql('userCoin')
            except Exception as e:
                self.logger.warning(e, "yunshi")
            
            self.send('[CQ:face,id=151] [CQ:at,qq='+str(uid)+']您的运势：\n桃花运：'+str(taohua)+'\n事业运：'+str(shiye)+'\n财运：'+str(cai)+'\n运势：'+zongstr)
        else:
            shiye = ob.get('shiye')
            taohua = ob.get('taohua')
            cai = ob.get('cai')
            zongstr = ob.get('zong')
            
            self.send('[CQ:face,id=151] [CQ:at,qq='+str(uid)+']\n你今天已经测过运势了喵~\n命运是不可以改变的喵~\n\>w</\n桃花运：'+str(taohua)+'\n事业运：'+str(shiye)+'\n财运：'+str(cai)+'\n运势：'+zongstr)
        
    def shengchenghonglian(self):
        uid = self.data.se.get('user_id')
        gid = self.data.se.get('group_id')
        message = self.data.message
        
        self.send('正在努力生成...')
        
        self.data.message = 'https://c.pc.qq.com/middlem.html?pfurl='+str(message)+' 1 shengchenghonglian.png'
        self.getWP()
    
    def addBiliSub(self):
        if not self.mysql.selectx("SELECT * FROM `botBiliDynamic` WHERE `uid`=%s", (self.data.message)):
            dynamic_id = getDynamic(self.data.message)
            self.mysql.commonx("INSERT INTO `botBiliDynamic` (`uid`, `offset`) VALUES (%s, %s)", (self.data.message, dynamic_id))
        if not self.mysql.selectx("SELECT * FROM `botBiliDynamicQn` WHERE `uid`=%s AND `qn`=%s", (self.data.message, self.data.se.get("group_id"))):
            self.mysql.commonx("INSERT INTO `botBiliDynamicQn` (`uid`, `qn`, `uuid`) VALUES (%s, %s, %s)", (self.data.message, self.data.se.get("group_id"), self.data.uuid))
            self.send("{}关注成功！".format(self.data.message))
        else:
            self.send("本群已关注过{}了！".format(self.data.message))
        
    
    def delBiliSub(self):
        self.mysql.commonx("DELETE FROM `botBiliDynamicQn` WHERE `uid`=%s AND `qn`=%s", (self.data.message, self.data.se.get("group_id")))
        if not self.mysql.selectx("SELECT * FROM `botBiliDynamicQn` WHERE `uid`=%s", (self.data.message)):
            self.mysql.commonx("DELETE FROM `botBiliDynamic` WHERE `uid`=%s", (self.data.message))
        self.send("已取关{}！".format(self.data.message))
    
    def listBiliSub(self):
        data = self.mysql.selectx("SELECT * FROM `botBiliDynamicQn` WHERE `qn`=%s", (self.data.se.get("group_id")))
        if not data:
            return self.send("本群还没有关注UP猪哦~")
        message = "face54 本群关注列表："
        for i in data:
            message += "\nUID: {}".format(i.get("uid"))
        self.send(message)


# apscheduler
def scheNotice(**kwargs):
    qn, content, uuid = kwargs.get('qn'), kwargs.get('content'), kwargs.get('uuid')
    assert qn, content, uuid
    


def BilibiliSub():
    botIns = PBF(Struct())
    try:
        for i in botIns.mysql.selectx("SELECT * FROM `botBiliDynamic`;"):
            try:
                dynamic_id = getDynamic(i.get("uid"))
            except Exception as e:
                # scheduler.pause_job("test_tick")
                # time.sleep(60)
                # scheduler.resume_job("test_tick")
                return
            if str(dynamic_id) != str(i.get("offset")):
                botIns.logger.info("find new dynamic {}".format(dynamic_id), "scheduler")
                botIns.mysql.commonx("UPDATE `botBiliDynamic` SET `offset`=%s WHERE `uid`=%s", (dynamic_id, i.get("uid")))
                filename = sync(screenshotDynamic(dynamic_id))
                print("filename", filename)
                qnList = botIns.mysql.selectx("SELECT * FROM `botBiliDynamicQn` WHERE `uid`=%s", (i.get("uid")))
                for l in qnList:
                    try:
                        botIns.logger.info("send: {}".format(l.get("qn")), "scheduler")
                        botIns.client.data.uuid = l.get("uuid")
                        botIns.client.data.botSettings = None
                        botIns.client.msg("爷爷，你关注的UP猪（{}）发动态啦！\n[https://t.bilibili.com/{}]\n[CQ:image,cache=0,file=https://pbfresources.xzynb.top/createimg/{}]".format(i.get("uid"), dynamic_id, filename)).custom(None, l.get("qn"))
                    except Exception as e:
                        pass
            time.sleep(2)
    except Exception as e:
        botIns.logger.warning(traceback.format_exc(), "scheduler")