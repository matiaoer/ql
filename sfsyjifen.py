#变量名：sfsyUrl
#格式：多账号用&分割或创建多个变量sfsyUrl
#关于变量值可选以下任一：
#❶sessionId=xxxx; _login_mobile_=xxxx; _login_user_id_=xxxx
#❷url编码后的SingUrl，可访问https://www.toolhelper.cn/EncodeDecode/Url进行编码

#注意：必须完成以下 QL_CLIENT_ID 和 QL_CLIENT_SECRET 配置

import hashlib
import json
import os
import random
import time
from datetime import datetime, timedelta
from sys import exit
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from urllib.parse import unquote

# ================= 青龙面板配置区域 (必须配置) =================
# 注意：你需要先在青龙面板 -> 系统设置 -> 应用设置 -> 新建应用 (权限选"环境变量")
# 获取 Client ID 和 Client Secret 填入下方，或在环境变量中添加同名变量

# 面板地址 (通常是 http://127.0.0.1:5700)
QL_URL = os.getenv('QL_URL', 'http://127.0.0.1:5700')

# 应用 Client ID
QL_CLIENT_ID = os.getenv('QL_CLIENT_ID', '填这里') 

# 应用 Client Secret
QL_CLIENT_SECRET = os.getenv('QL_CLIENT_SECRET', '填这里')
# =============================================

# 禁用安全请求警告
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
EXCHANGE_RANGE = os.getenv('SFSY_DHJE', '23-15')  # 默认：23-15
FORCE_EXCHANGE = os.getenv('SFSY_DH', 'false').lower() == 'true'  # 默认：false
MAX_EXCHANGE_TIMES = int(os.getenv('SFSY_DHCS', '3'))  # 默认：3
PROXY_API_URL = os.getenv('SF_PROXY_API_URL', '')  # 从环境变量获取代理API地址
AVAILABLE_AMOUNTS = ['23元', '20元', '15元', '10元', '5元', '3元', '2元', '1元']

def parse_exchange_range(exchange_range):
    if '-' in exchange_range:
        try:
            start_val, end_val = exchange_range.split('-')
            start_val = int(start_val.strip())
            end_val = int(end_val.strip())
            
            target_amounts = []
            for amount in AVAILABLE_AMOUNTS:
                amount_val = int(amount.replace('元', ''))
                if end_val <= amount_val <= start_val:
                    target_amounts.append(amount)
            
            return target_amounts
        except:
            print(f"❌ 兑换区间配置错误: {exchange_range}")
            return ['23元']  # 默认返回23元
    else:
        if exchange_range.endswith('元'):
            return [exchange_range]
        else:
            return [f"{exchange_range}元"]

def get_proxy():
    try:
        if not PROXY_API_URL:
            print('\n⚠️ 未配置代理API地址，将不使用代理')
            return None
            
        response = requests.get(PROXY_API_URL, timeout=10)
        if response.status_code == 200:
            proxy_text = response.text.strip()
            if ':' in proxy_text:
                proxy = f'http://{proxy_text}'
                return {
                    'http': proxy,
                    'https': proxy
                }
        print(f'\n❌ 获取代理失败: {response.text}')
        return None
    except Exception as e:
        print(f'\n❌ 获取代理异常: {str(e)}')
        return None

send_msg = ''
one_msg = ''

def Log(cont=''):
    global send_msg, one_msg
    print(cont)
    if cont:
        one_msg += f'{cont}\n'
        send_msg += f'{cont}\n'

inviteId = ['']

class QLManager:
    def __init__(self):
        self.url = QL_URL.rstrip('/')
        self.client_id = QL_CLIENT_ID
        self.client_secret = QL_CLIENT_SECRET
        self.token = None
        self.token_expire = 0

    def get_token(self):
        if self.token and time.time() < self.token_expire:
            return self.token
        
        url = f"{self.url}/open/auth/token?client_id={self.client_id}&client_secret={self.client_secret}"
        try:
            res = requests.get(url, timeout=5).json()
            if res.get('code') == 200:
                self.token = res['data']['token']
                self.token_expire = time.time() + res['data']['expiration'] - 60 
                return self.token
        except Exception as e:
            print(f"❌ [QL] 获取 Token 失败: {e}")
        return None

    def get_env_ids(self, name):
        token = self.get_token()
        if not token: return []
        
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.url}/open/envs?searchValue={name}" 
        try:
            res = requests.get(url, headers=headers, timeout=5).json()
            if res.get('code') == 200:
                id_list = [
                    item['id'] for item in res['data'] 
                    if item['name'] == name and item.get('status') == 0
                ]
                if not id_list and res['data']:
                    id_list = [item['id'] for item in res['data'] if item['name'] == name]
                return id_list
        except Exception as e:
            print(f"❌ [QL] 获取变量 ID 列表失败: {e}")
        return []

    def get_env_details(self, env_id):
        token = self.get_token()
        if not token: return None, None
        
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.url}/open/envs/{env_id}"
        try:
            res = requests.get(url, headers=headers, timeout=5).json()
            if res.get('code') == 200:
                return res['data']['value'], res['data'].get('remarks', '')
        except Exception as e:
            print(f"❌ [QL] 获取 ID {env_id} 详情失败: {e}")
        return None, None

    def update_env(self, env_id, name, value, remarks=""):
        token = self.get_token()
        if not token: return False
        
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        url = f"{self.url}/open/envs"
        data = {
            "name": name,
            "value": value,
            "id": env_id,
            "remarks": remarks
        }
        try:
            res = requests.put(url, headers=headers, json=data, timeout=5).json()
            return res.get('code') == 200
        except Exception as e:
            print(f"❌ [QL] 更新变量 {env_id} 失败: {e}")
            return False

class RUN:
    def __init__(self, info, index, ql_id, sub_index):
        global one_msg
        one_msg = ''
        split_info = info.split('@')
        url = split_info[0]
        len_split_info = len(split_info)
        last_info = split_info[len_split_info - 1]
        self.send_UID = None
        if len_split_info > 0 and "UID_" in last_info:
            self.send_UID = last_info
        
        self.index = index + 1

        self.proxy = get_proxy()
        if self.proxy:
            print(f"✅ 成功获取代理: {self.proxy['http']}")
        
        self.s = requests.session()
        self.s.verify = False
        if self.proxy:
            self.s.proxies = self.proxy
            
        self.headers = {
            'Host': 'mcs-mimp-web.sf-express.com',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36 NetType/WIFI MicroMessenger/7.0.20.1781(0x6700143B) WindowsWechat(0x63090551) XWEB/6945 Flue',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'sec-fetch-site': 'none',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-user': '?1',
            'sec-fetch-dest': 'document',
            'accept-language': 'zh-CN,zh',
            'platform': 'MINI_PROGRAM',
        }
        
        self.login_res = self.login(url)
        self.all_logs =[] 
        self.today = datetime.now().strftime('%Y-%m-%d')
        self.member_day_black = False
        self.member_day_red_packet_drew_today = False
        self.member_day_red_packet_map = {}
        self.max_level = 8
        self.packet_threshold = 1 << (self.max_level - 1)
        self.is_last_day = False
        self.auto_exchanged = False
        self.exchange_count = 0
        self.force_exchange = FORCE_EXCHANGE
        self.totalPoint = 0
        self.usableHoney = 0
        self.activityEndTime = ""
        self.target_amounts = parse_exchange_range(EXCHANGE_RANGE)

    def get_deviceId(self, characters='abcdef0123456789'):
        result = ''
        for char in 'xxxxxxxx-xxxx-xxxx':
            if char == 'x':
                result += random.choice(characters)
            elif char == 'X':
                result += random.choice(characters).upper()
            else:
                result += char
        return result


    def get_cache_path(self):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            return os.path.join(script_dir, "sf_all_cookies.json")
        except:
            return "sf_all_cookies.json"

    def load_cookie(self):
        try:
            import fcntl
            path = self.get_cache_path()
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                    try:
                        all_cookies = json.load(f)
                        my_cookies = all_cookies.get(self.cache_key)
                        if my_cookies:
                            self.s.cookies = requests.utils.cookiejar_from_dict(my_cookies)
                            return True
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            Log(f"⚠️ 读取缓存失败: {str(e)}")
        return False

    def save_cookie(self):
        try:
            import fcntl
            path = self.get_cache_path()
            all_cookies = {}
            
            if not os.path.exists(path):
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump({}, f)

            with open(path, 'r+', encoding='utf-8') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    try:
                        content = f.read()
                        if content:
                            all_cookies = json.loads(content)
                    except:
                        pass 
                    
                    all_cookies[self.cache_key] = requests.utils.dict_from_cookiejar(self.s.cookies)
                    
                    f.seek(0)
                    f.truncate()
                    json.dump(all_cookies, f, ensure_ascii=False, indent=4)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except Exception as e:
            Log(f"⚠️ 保存缓存失败: {str(e)}")

    def check_cookie_valid(self):
        try:
            json_data = {'channelType': '1', 'deviceId': self.get_deviceId()}
            url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~integralTaskStrategyService~queryPointTaskAndSignFromES'
            response = self.do_request(url, data=json_data, max_retries=1)
            if response and response.get('success') == True:
                return True
        except:
            pass
        return False

    def login(self, sfurl):
        sfurl = unquote(sfurl)
        if 'sessionId=' in sfurl and '_login_mobile_=' in sfurl:
            cookie_dict = {}
            for item in sfurl.split(';'):
                item = item.strip()
                if '=' in item:
                    k, v = item.split('=', 1)
                    cookie_dict[k] = v
            
            for k, v in cookie_dict.items():
                self.s.cookies.set(k, v, domain='mcs-mimp-web.sf-express.com')
            
            self.user_id = cookie_dict.get('_login_user_id_', '')
            self.phone = cookie_dict.get('_login_mobile_', '')
            self.session_id = cookie_dict.get('sessionId', '')
            
            if self.phone and self.session_id:
                self.mobile = self.phone[:3] + "*" * 4 + self.phone[7:]
                if self.check_cookie_valid():
                    Log(f'ℹ️ 账号{self.index}:【{self.mobile}】标准CK验证有效，直接进入任务模式')
                    self.standard_cookie = sfurl  
                    return True
                else:
                    Log(f'⚠️ 账号{self.index}: 标准CK已失效')
                    return False
        
        elif sfurl.startswith(('http://', 'https://')):
            decoded_url = sfurl
            retry_count = 0
            max_retries = 3

            while retry_count < max_retries:
                try:

                    ress = self.s.get(decoded_url, headers=self.headers, timeout=30)

                    self.user_id = self.s.cookies.get_dict().get('_login_user_id_', '')
                    self.phone = self.s.cookies.get_dict().get('_login_mobile_', '')
                    self.session_id = self.s.cookies.get_dict().get('sessionId', '')
                    
                    if self.phone and self.session_id:
                        self.mobile = self.phone[:3] + "*" * 4 + self.phone[7:]
                        Log(f'👤 账号{self.index}:【{self.mobile}】SignURL解析并提取CK参数成功')

                        self.standard_cookie = f"sessionId={self.session_id}; _login_mobile_={self.phone}; _login_user_id_={self.user_id}"
                        return True
                    else:
                        Log(f'❌ 账号{self.index}: SignURL 解析用户信息失败')
                        return False

                except requests.exceptions.RequestException as e:
                    retry_count += 1
                    Log(f'⚠️ 网络异常 ({retry_count}/{max_retries}): {str(e)}')
                    if retry_count < max_retries:
                        Log(f'🔄 检测到网络故障，正在切换新代理重试...')
                        self.proxy = get_proxy()
                        if self.proxy:
                            self.s.proxies = self.proxy
                        time.sleep(2)
                    else:
                        Log(f'❌ 提取网络最终失败')
                        return False
                except Exception as e:
                    Log(f'❌ 解析未知异常: {str(e)}')
                    return False
                    
        Log(f'❌ 账号{self.index}: 环境变量格式无法识别')
        return False
       

    def getSign(self):
        timestamp = str(int(round(time.time() * 1000)))
        token = 'wwesldfs29aniversaryvdld29'
        sysCode = 'MCS-MIMP-CORE'
        data = f'token={token}&timestamp={timestamp}&sysCode={sysCode}'
        signature = hashlib.md5(data.encode()).hexdigest()
        data = {
            'sysCode': sysCode,
            'timestamp': timestamp,
            'signature': signature
        }
        self.headers.update(data)
        return data

    def do_request(self, url, data={}, req_type='post', max_retries=3):
        self.getSign()
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                if req_type.lower() == 'get':
                    response = self.s.get(url, headers=self.headers, timeout=30)
                elif req_type.lower() == 'post':
                    response = self.s.post(url, headers=self.headers, json=data, timeout=30)
                else:
                    raise ValueError('Invalid req_type: %s' % req_type)
                    
                response.raise_for_status()
                
                try:
                    res = response.json()
                    return res
                except json.JSONDecodeError as e:
                    print(f'JSON解析失败: {str(e)}, 响应内容: {response.text[:200]}')
                    retry_count += 1
                    if retry_count < max_retries:
                        print(f'正在进行第{retry_count + 1}次重试...')
                        time.sleep(2)
                        continue
                    return None
                    
            except requests.exceptions.RequestException as e:
                retry_count += 1
                if retry_count < max_retries:
                    print(f'请求失败，正在切换代理重试 ({retry_count}/{max_retries}): {str(e)}')
                    self.proxy = get_proxy()
                    if self.proxy:
                        print(f"✅ 成功获取新代理: {self.proxy['http']}")
                        self.s.proxies = self.proxy
                    time.sleep(2)
                else:
                    print('请求最终失败:', e)
                    return None
                
        return None

    def sign(self):
        print(f'🎯 开始执行WX端签到')
        json_data = {"comeFrom": "vioin", "channelFrom": "WEIXIN"}
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~integralTaskSignPlusService~automaticSignFetchPackage'
        response = self.do_request(url, data=json_data)
        if response.get('success') == True:
            count_day = response.get('obj', {}).get('countDay', 0)
            if response.get('obj') and response['obj'].get('integralTaskSignPackageVOList'):
                packet_name = response["obj"]["integralTaskSignPackageVOList"][0]["packetName"]
                Log(f'✨ WX端签到成功，获得【{packet_name}】，已连签【{count_day}】天')
            else:
                Log(f'📝 今日WX端已签到，已连签【{count_day}】天')
        else:
            print(f'❌ WX端签到失败！原因：{response.get("errorMessage")}')

    def sign_app(self):
        print(f'🎯 开始执行APP端签到')
        json_data = {"comeFrom": "vioin", "channelFrom": "SFAPP"}
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~integralTaskSignPlusService~automaticSignFetchPackage'
        response = self.do_request(url, data=json_data)
        if response.get('success') == True:
            count_day = response.get('obj', {}).get('countDay', 0)
            if response.get('obj') and response['obj'].get('integralTaskSignPackageVOList'):
                packet_name = response["obj"]["integralTaskSignPackageVOList"][0]["packetName"]
                Log(f'✨ APP端签到成功，获得【{packet_name}】，已连签【{count_day}】天')
            else:
                Log(f'📝 今日APP端已签到，已连签【{count_day}】天')
        else:
            print(f'📝 APP端签到跳过：{response.get("errorMessage")}')

    def receive_sign_rewards(self):
        print(f'🎁 检查并补领签到奖励')
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~integralTaskSignPlusService~getUnFetchPointAndDiscount'
        response = self.do_request(url)
        if response.get('success') == True and response.get('obj'):
            count = len(response['obj'])
            print(f'👉 发现 {count} 个未领取奖励，开始补领...')
            for reward in response['obj']:
                packet_name = reward.get('packetName', '未知奖励')
                receive_url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberIntegral~packetService~receivePacket'
                receive_data = {"packageId": reward['packageId']}
                time.sleep(1)
                res = self.do_request(receive_url, data=receive_data)
                if res.get('success') == True:
                    Log(f'✨ 成功补领：【{packet_name}】')
                else:
                    error_msg = res.get("errorMessage", "")
                    if "系统繁忙" in error_msg:
                        Log(f'✨ 成功补领：【{packet_name}】(系统返回繁忙但已处理)')
                    else:
                        Log(f'❌ 补领异常：{error_msg}，请稍后核实积分')
        else:
            print(f'📝 暂无未领取的签到奖励')

    def superWelfare_receiveRedPacket(self):
        print(f'🎁 超值福利签到')
        json_data = {
            'channel': 'czflqdlhbxcx'
        }
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberActLengthy~redPacketActivityService~superWelfare~receiveRedPacket'
        response = self.do_request(url, data=json_data)
        if response.get('success') == True:
            gift_list = response.get('obj', {}).get('giftList', [])
            if response.get('obj', {}).get('extraGiftList', []):
                gift_list.extend(response['obj']['extraGiftList'])
            gift_names = ', '.join([gift['giftName'] for gift in gift_list])
            receive_status = response.get('obj', {}).get('receiveStatus')
            status_message = '领取成功' if receive_status == 1 else '已领取过'
            Log(f'🎉 超值福利签到[{status_message}]: {gift_names}')
        else:
            error_message = response.get('errorMessage') or json.dumps(response) or '无返回'
            print(f'❌ 超值福利签到失败: {error_message}')


    def get_SignTaskList(self, END=False):
        if not END: print(f'🎯 开始获取签到任务列表')
        target_channels = ['1', '2', '3', '4'] if not END else ['1']
        processed_tasks = set()
        for channel in target_channels:
            json_data = {'channelType': channel, 'deviceId': self.get_deviceId()}
            url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~integralTaskStrategyService~queryPointTaskAndSignFromES'
            response = self.do_request(url, data=json_data)
            #print(json.dumps(response, ensure_ascii=False))
            if response.get('success') == True and response.get('obj') != []:
                self.totalPoint = response["obj"]["totalPoint"]
                if END:
                    Log(f'💰 当前积分：【{self.totalPoint}】')
                    return
                if channel == '1': Log(f'💰 执行前积分：【{self.totalPoint}】')
                for task in response["obj"]["taskTitleLevels"]:
                    self.taskId = task["taskId"]
                    if self.taskId in processed_tasks: continue
                    processed_tasks.add(self.taskId)
                    self.taskCode = task["taskCode"]
                    self.strategyId = task["strategyId"]
                    self.title = task["title"]
                    status = task["status"]
                    skip_title = ['用行业模板寄件下单', '去新增一个收件偏好', '参与积分活动', '用积分兑任意礼品', '去使用AI寄件', '设置你的顺丰ID']
                    if status == 3:
                        print(f'✨ {self.title}-已完成')
                        continue
                    if self.title in skip_title:
                        print(f'⏭️ {self.title}-跳过')
                        continue
                    else:
                        
                        if '领任意生活特权福利' in self.title:
                            self.get_coupom_list()
                     
                        else:
                            jump_url = task.get('taskJumpAddress', '')
                            if jump_url and jump_url.startswith('http'):                           
                                try:
                                    self.s.get(jump_url, headers=self.headers, timeout=10)
                                except: pass
    
                            if not self.taskCode and task.get('buttonRedirect'):
                                import re
                                btn_url = task['buttonRedirect']
                                decoded_url = unquote(btn_url)
                                taskId_match = re.search(r'"taskId"\s*:\s*"(\w+)"', decoded_url)
                                if taskId_match: self.taskCode = taskId_match.group(1)
                                if btn_url.startswith('http'):
                                    try:
                                        self.s.get(btn_url, headers=self.headers, timeout=10)
                                    except: pass
                        
                        self.doTask()
                        time.sleep(2)
                    self.receiveTask()
                    

    def doTask(self):
        print(f'🎯 开始去完成【{self.title}】任务')
        json_data = {'taskCode': self.taskCode}
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonRoutePost/memberEs/taskRecord/finishTask'
        
        #print(f'👇 [请求] URL: {url}')
        #print(f'👇 [请求] Data: {json.dumps(json_data, ensure_ascii=False)}')
        
        response = self.do_request(url, data=json_data)
        
        #print(f'👆 [响应] Body: {json.dumps(response, ensure_ascii=False)}')
        
        if response.get('success') == True:
            print(f'✨ 【{self.title}】任务-已完成')
        else:
            print(f'❌ 【{self.title}】任务-{response.get("errorMessage")}')

    def receiveTask(self):
        print(f'🎁 开始领取【{self.title}】任务奖励')
        json_data = {
            "strategyId": self.strategyId,
            "taskId": self.taskId,
            "taskCode": self.taskCode,
            "deviceId": self.get_deviceId()
        }
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~integralTaskStrategyService~fetchIntegral'
        
        #print(f'👇 [请求] URL: {url}')
        #print(f'👇 [请求] Data: {json.dumps(json_data, ensure_ascii=False)}')
        
        response = self.do_request(url, data=json_data)
        
        #print(f'👆 [响应] Body: {json.dumps(response, ensure_ascii=False)}')
        
        if response.get('success') == True:
            print(f'✨ 【{self.title}】任务奖励领取成功！')
        else:
            print(f'❌ 【{self.title}】任务-{response.get("errorMessage")}')

    def do_honeyTask(self):
        # 做任务
        json_data = {"taskCode": self.taskCode}
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberEs~taskRecord~finishTask'
        response = self.do_request(url, data=json_data)
        if response.get('success') == True:
            print(f'>【{self.taskType}】任务-已完成')
        else:
            print(f'>【{self.taskType}】任务-{response.get("errorMessage")}')

    def receive_honeyTask(self):
        print('>>>执行收取丰蜜任务')
        # 收取
        self.headers['syscode'] = 'MCS-MIMP-CORE'
        self.headers['channel'] = 'wxwdsj'
        self.headers['accept'] = 'application/json, text/plain, */*'
        self.headers['content-type'] = 'application/json;charset=UTF-8'
        self.headers['platform'] = 'MINI_PROGRAM'
        json_data = {"taskType": self.taskType}
        # print(json_data)
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~receiveExchangeIndexService~receiveHoney'
        response = self.do_request(url, data=json_data)
        if response.get('success') == True:
            print(f'收取任务【{self.taskType}】成功！')
        else:
            print(f'收取任务【{self.taskType}】失败！原因：{response.get("errorMessage")}')


    def get_coupom(self, goods):
            # 领取单个权益
            json_data = {
                "from": "Point_Mall",
                "orderSource": "POINT_MALL_EXCHANGE",
                "goodsNo": goods['goodsNo'],
                "quantity": 1,
                "taskCode": self.taskCode
            }
            url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberGoods~pointMallService~createOrder'
            response = self.do_request(url, data=json_data)
            if response.get('success') == True:
                print(f'✨ 成功领取权益：{goods.get("goodsName", "未知权益")}')
                return True
            else:
                print(f'❌ 领取权益失败：{response.get("errorMessage")}')
                return False

    def push_common_order_h5(self, goods):
            # 模拟点击生活服务类的H5权益（如顺丰同城）
            print(f'👉 正在浏览H5权益：{goods.get("goodsName", "未知")}')
            json_data = goods.copy()
            json_data.update({
                "orderSource": "H5",
                "taskCode": self.taskCode,
                "from": "LIFE_MALL_EXCHANGE"
            })
            url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberGoods~pointMallService~pushCommonOrderInfoH5'
            response = self.do_request(url, data=json_data)
            if response.get('success') == True:
                print(f'✨ 浏览H5权益成功，任务应已完成')
                return True
            else:
                print(f'❌ 浏览H5权益失败：{response.get("errorMessage")}')
                return False

    def get_coupom_list(self):
        # 获取权益列表并尝试领取
        print('🎁 正在获取生活特权列表...')
        json_data = {
            "memGrade": 2,
            "categoryCode": "SHTQ",
            "showCode": "SHTQWNTJ"
        }
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberGoods~mallGoodsLifeService~list'
        response = self.do_request(url, data=json_data)

        if response.get('success') == True:
            all_goods = []
            # 优先策略：寻找“生活服务”模块下的 SFH5 类型商品（如顺丰同城），只需点击无需领取
            if response.get("obj"):
                for module in response["obj"]:
                    module_title = module.get("moduleTitle", "")
                    goods_list = module.get("goodsList", [])
                    
                    # 策略1：优先完成“生活服务”下的点击任务（无消耗）
                    if "生活服务" in module_title:
                        for goods in goods_list:
                            # 抓包显示顺丰同城类型为 SFH5，且名字通常包含顺丰同城
                            if goods.get('goodsType') == 'SFH5' and "顺丰同城" in goods.get('goodsName', ''):
                                if self.push_common_order_h5(goods):
                                    time.sleep(2)
                                    return
                    
                    all_goods.extend(goods_list)

            # 策略2：原有逻辑，如果上面没找到，尝试领取一个免费权益
            print('⚠️ 未找到指定的H5权益，尝试领取免费券...')
            for goods in all_goods:
                exchange_times_limit = goods.get('exchangeTimesLimit', 0)
                # 排除需要积分的（虽然SHTQ通常是免费的，但保险起见）
                points = goods.get('integral', 0)
                if exchange_times_limit >= 1 and points == 0:
                    if self.get_coupom(goods):
                        time.sleep(2)
                        return # 领一个就够了
            print('📝 没有可领取的免费权益，或所有权益已领完')
        else:
            print(f'❌ 获取权益列表失败: {response.get("errorMessage")}')


    def get_honeyTaskListStart(self):
        print('🍯 开始获取采蜜换大礼任务列表')
        json_data = {}
        self.headers['channel'] = 'wxwdsj'
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~receiveExchangeIndexService~taskDetail'

        response = self.do_request(url, data=json_data)
        if response.get('success') == True:
            for item in response["obj"]["list"]:
                self.taskType = item["taskType"]
                status = item["status"]
                if status == 3:
                    print(f'✨ 【{self.taskType}】-已完成')
                    continue
                if "taskCode" in item:
                    self.taskCode = item["taskCode"]
                    if self.taskType == 'DAILY_VIP_TASK_TYPE':
                        self.get_coupom_list()
                    else:
                        self.do_honeyTask()
                if self.taskType == 'BEES_GAME_TASK_TYPE':
                    self.honey_damaoxian()
                time.sleep(2)

    def honey_damaoxian(self):
        print('>>>执行大冒险任务')
        gameNum = 5
        for i in range(1, gameNum):
            json_data = {
                'gatherHoney': 20,
            }
            if gameNum < 0: break
            print(f'>>开始第{i}次大冒险')
            url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~receiveExchangeGameService~gameReport'
            response = self.do_request(url, data=json_data)
            stu = response.get('success')
            if stu:
                gameNum = response.get('obj')['gameNum']
                print(f'>大冒险成功！剩余次数【{gameNum}】')
                time.sleep(2)
                gameNum -= 1
            elif response.get("errorMessage") == '容量不足':
                print(f'> 需要扩容')
                self.honey_expand()
            else:
                print(f'>大冒险失败！【{response.get("errorMessage")}】')
                break

    def honey_expand(self):
        print('>>>容器扩容')
        gameNum = 5

        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~receiveExchangeIndexService~expand'
        response = self.do_request(url, data={})
        stu = response.get('success', False)
        if stu:
            obj = response.get('obj')
            print(f'>成功扩容【{obj}】容量')
        else:
            print(f'>扩容失败！【{response.get("errorMessage")}】')

    def honey_indexData(self, END=False):
        if not END: print('--------------------------------\n🍯 开始执行采蜜换大礼任务')
        random_invite = random.choice([invite for invite in inviteId if invite != self.user_id])
        self.headers['channel'] = 'wxwdsj'
        json_data = {"inviteUserId": random_invite}
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~receiveExchangeIndexService~indexData'
        response = self.do_request(url, data=json_data)
        if response.get('success') == True:
            self.usableHoney = response.get('obj').get('usableHoney')
            activityEndTime = response.get('obj').get('activityEndTime', '')
            
            if activityEndTime:
                try:
                    self.activityEndTime = activityEndTime.split()[0] if ' ' in activityEndTime else activityEndTime
                    activity_end_time = datetime.strptime(activityEndTime, "%Y-%m-%d %H:%M:%S")
                    current_time = datetime.now()
                    
                    if current_time.date() == activity_end_time.date():
                        self.is_last_day = True
                        if not END:
                            Log(f"⏳ 本期活动今日结束，尝试自动兑换券！目标：{' > '.join(self.target_amounts)}")
                            if not self.auto_exchanged:
                                exchange_success = self.exchange_23_coupon()
                                if exchange_success:
                                    self.auto_exchanged = True
                except Exception as e:
                    print(f'处理活动时间异常: {str(e)}')
                    self.activityEndTime = activityEndTime
            
            if not END:
                Log(f'🍯 执行前丰蜜：【{self.usableHoney}】')
                if activityEndTime and not self.is_last_day:
                    print(f'📅 本期活动结束时间【{activityEndTime}】')
                    
                taskDetail = response.get('obj').get('taskDetail')
                if taskDetail != []:
                    for task in taskDetail:
                        self.taskType = task['type']
                        self.receive_honeyTask()
                        time.sleep(2)
            else:
                Log(f'🍯 执行后丰蜜：【{self.usableHoney}】')
                return

    def EAR_END_2023_TaskList(self):
        print('\n🎭 开始年终集卡任务')
        json_data = {
            "activityCode": "YEAREND_2024",
            "channelType": "MINI_PROGRAM"
        }
        self.headers['channel'] = '24nzdb'
        self.headers['platform'] = 'MINI_PROGRAM'
        self.headers['syscode'] = 'MCS-MIMP-CORE'

        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~activityTaskService~taskList'

        response = self.do_request(url, data=json_data)
        if response.get('success') == True:
            for item in response["obj"]:
                self.title = item["taskName"]
                self.taskType = item["taskType"]
                status = item["status"]
                if status == 3:
                    print(f'✨ 【{self.taskType}】-已完成')
                    continue
                if self.taskType == 'INTEGRAL_EXCHANGE':
                    print(f'⚠️ 积分兑换任务暂不支持')
                elif self.taskType == 'CLICK_MY_SETTING':
                    self.taskCode = item["taskCode"]
                    self.addDeliverPrefer()
                if "taskCode" in item:
                    self.taskCode = item["taskCode"]
                    self.doTask()
                    time.sleep(3)
                    self.receiveTask()
                else:
                    print(f'⚠️ 暂时不支持【{self.title}】任务')

    def addDeliverPrefer(self):
        print(f'>>>开始【{self.title}】任务')
        json_data = {
            "country": "中国",
            "countryCode": "A000086000",
            "province": "北京市",
            "provinceCode": "A110000000",
            "city": "北京市",
            "cityCode": "A111000000",
            "county": "东城区",
            "countyCode": "A110101000",
            "address": "1号楼1单元101",
            "latitude": "",
            "longitude": "",
            "memberId": "",
            "locationCode": "010",
            "zoneCode": "CN",
            "postCode": "",
            "takeWay": "7",
            "callBeforeDelivery": 'false',
            "deliverTag": "2,3,4,1",
            "deliverTagContent": "",
            "startDeliverTime": "",
            "selectCollection": 'false',
            "serviceName": "",
            "serviceCode": "",
            "serviceType": "",
            "serviceAddress": "",
            "serviceDistance": "",
            "serviceTime": "",
            "serviceTelephone": "",
            "channelCode": "RW11111",
            "taskId": self.taskId,
            "extJson": "{\"noDeliverDetail\":[]}"
        }
        url = 'https://ucmp.sf-express.com/cx-wechat-member/member/deliveryPreference/addDeliverPrefer'
        response = self.do_request(url, data=json_data)
        if response.get('success') == True:
            print('新增一个收件偏好，成功')
        else:
            print(f'>【{self.title}】任务-{response.get("errorMessage")}')

    def member_day_index(self):
        print('🎭 会员日活动')
        try:
            invite_user_id = random.choice([invite for invite in inviteId if invite != self.user_id])
            payload = {'inviteUserId': invite_user_id}
            url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~memberDayIndexService~index'

            response = self.do_request(url, data=payload)
            if response.get('success'):
                lottery_num = response.get('obj', {}).get('lotteryNum', 0)
                can_receive_invite_award = response.get('obj', {}).get('canReceiveInviteAward', False)
                if can_receive_invite_award:
                    self.member_day_receive_invite_award(invite_user_id)
                self.member_day_red_packet_status()
                Log(f'🎁 会员日可以抽奖{lottery_num}次')
                for _ in range(lottery_num):
                    self.member_day_lottery()
                if self.member_day_black:
                    return
                self.member_day_task_list()
                if self.member_day_black:
                    return
                self.member_day_red_packet_status()
            else:
                error_message = response.get('errorMessage', '无返回')
                Log(f'📝 查询会员日失败: {error_message}')
                if '没有资格参与活动' in error_message:
                    self.member_day_black = True
                    Log('📝 会员日任务风控')
        except Exception as e:
            print(e)

    def member_day_receive_invite_award(self, invite_user_id):
        try:
            payload = {'inviteUserId': invite_user_id}

            url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~memberDayIndexService~receiveInviteAward'

            response = self.do_request(url, payload)
            if response.get('success'):
                product_name = response.get('obj', {}).get('productName', '空气')
                Log(f'🎁 会员日奖励: {product_name}')
            else:
                error_message = response.get('errorMessage', '无返回')
                Log(f'📝 领取会员日奖励失败: {error_message}')
                if '没有资格参与活动' in error_message:
                    self.member_day_black = True
                    Log('📝 会员日任务风控')
        except Exception as e:
            print(e)

    def member_day_lottery(self):
        try:
            payload = {}
            url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~memberDayLotteryService~lottery'

            response = self.do_request(url, payload)
            if response.get('success'):
                product_name = response.get('obj', {}).get('productName', '空气')
                Log(f'🎁 会员日抽奖: {product_name}')
            else:
                error_message = response.get('errorMessage', '无返回')
                Log(f'📝 会员日抽奖失败: {error_message}')
                if '没有资格参与活动' in error_message:
                    self.member_day_black = True
                    Log('📝 会员日任务风控')
        except Exception as e:
            print(e)

    def member_day_task_list(self):
        try:
            payload = {'activityCode': 'MEMBER_DAY', 'channelType': 'MINI_PROGRAM'}
            url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~activityTaskService~taskList'

            response = self.do_request(url, payload)
            if response.get('success'):
                task_list = response.get('obj', [])
                for task in task_list:
                    if task['status'] == 1:
                        if self.member_day_black:
                            return
                        self.member_day_fetch_mix_task_reward(task)
                for task in task_list:
                    if task['status'] == 2:
                        if self.member_day_black:
                            return
                        if task['taskType'] in ['SEND_SUCCESS', 'INVITEFRIENDS_PARTAKE_ACTIVITY', 'OPEN_SVIP',
                                                'OPEN_NEW_EXPRESS_CARD', 'OPEN_FAMILY_CARD', 'CHARGE_NEW_EXPRESS_CARD',
                                                'INTEGRAL_EXCHANGE']:
                            pass
                        else:
                            for _ in range(task['restFinishTime']):
                                if self.member_day_black:
                                    return
                                self.member_day_finish_task(task)
            else:
                error_message = response.get('errorMessage', '无返回')
                Log('📝 查询会员日任务失败: ' + error_message)
                if '没有资格参与活动' in error_message:
                    self.member_day_black = True
                    Log('📝 会员日任务风控')
        except Exception as e:
            print(e)

    def member_day_finish_task(self, task):
        try:
            payload = {'taskCode': task['taskCode']}

            url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberEs~taskRecord~finishTask'

            response = self.do_request(url, payload)
            if response.get('success'):
                Log('📝 完成会员日任务[' + task['taskName'] + ']成功')
                self.member_day_fetch_mix_task_reward(task)
            else:
                error_message = response.get('errorMessage', '无返回')
                Log('📝 完成会员日任务[' + task['taskName'] + ']失败: ' + error_message)
                if '没有资格参与活动' in error_message:
                    self.member_day_black = True
                    Log('📝 会员日任务风控')
        except Exception as e:
            print(e)

    def member_day_fetch_mix_task_reward(self, task):
        try:
            payload = {'taskType': task['taskType'], 'activityCode': 'MEMBER_DAY', 'channelType': 'MINI_PROGRAM'}

            url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~activityTaskService~fetchMixTaskReward'

            response = self.do_request(url, payload)
            if response.get('success'):
                Log('🎁 领取会员日任务[' + task['taskName'] + ']奖励成功')
            else:
                error_message = response.get('errorMessage', '无返回')
                Log('📝 领取会员日任务[' + task['taskName'] + ']奖励失败: ' + error_message)
                if '没有资格参与活动' in error_message:
                    self.member_day_black = True
                    Log('📝 会员日任务风控')
        except Exception as e:
            print(e)

    def member_day_receive_red_packet(self, hour):
        try:
            payload = {'receiveHour': hour}
            url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~memberDayTaskService~receiveRedPacket'

            response = self.do_request(url, payload)
            if response.get('success'):
                print(f'🎁 会员日领取{hour}点红包成功')
            else:
                error_message = response.get('errorMessage', '无返回')
                print(f'📝 会员日领取{hour}点红包失败: {error_message}')
                if '没有资格参与活动' in error_message:
                    self.member_day_black = True
                    Log('📝 会员日任务风控')
        except Exception as e:
            print(e)

    def member_day_red_packet_status(self):
        try:
            payload = {}
            url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~memberDayPacketService~redPacketStatus'
            response = self.do_request(url, payload)
            if response.get('success'):
                packet_list = response.get('obj', {}).get('packetList', [])
                for packet in packet_list:
                    self.member_day_red_packet_map[packet['level']] = packet['count']

                for level in range(1, self.max_level):
                    count = self.member_day_red_packet_map.get(level, 0)
                    while count >= 2:
                        self.member_day_red_packet_merge(level)
                        count -= 2
                packet_summary = []
                remaining_needed = 0

                for level, count in self.member_day_red_packet_map.items():
                    if count == 0:
                        continue
                    packet_summary.append(f"[{level}级]X{count}")
                    int_level = int(level)
                    if int_level < self.max_level:
                        remaining_needed += 1 << (int_level - 1)

                Log("📝 会员日合成列表: " + ", ".join(packet_summary))

                if self.member_day_red_packet_map.get(self.max_level):
                    Log(f"🎁 会员日已拥有[{self.max_level}级]红包X{self.member_day_red_packet_map[self.max_level]}")
                    self.member_day_red_packet_draw(self.max_level)
                else:
                    remaining = self.packet_threshold - remaining_needed
                    Log(f"📝 会员日距离[{self.max_level}级]红包还差: [1级]红包X{remaining}")

            else:
                error_message = response.get('errorMessage', '无返回')
                Log(f'📝 查询会员日合成失败: {error_message}')
                if '没有资格参与活动' in error_message:
                    self.member_day_black = True
                    Log('📝 会员日任务风控')
        except Exception as e:
            print(e)

    def member_day_red_packet_merge(self, level):
        try:
            # for key,level in enumerate(self.member_day_red_packet_map):
            #     pass
            payload = {'level': level, 'num': 2}
            url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~memberDayPacketService~redPacketMerge'

            response = self.do_request(url, payload)
            if response.get('success'):
                Log(f'🎁 会员日合成: [{level}级]红包X2 -> [{level + 1}级]红包')
                self.member_day_red_packet_map[level] -= 2
                if not self.member_day_red_packet_map.get(level + 1):
                    self.member_day_red_packet_map[level + 1] = 0
                self.member_day_red_packet_map[level + 1] += 1
            else:
                error_message = response.get('errorMessage', '无返回')
                Log(f'📝 会员日合成两个[{level}级]红包失败: {error_message}')
                if '没有资格参与活动' in error_message:
                    self.member_day_black = True
                    Log('📝 会员日任务风控')
        except Exception as e:
            print(e)

    def member_day_red_packet_draw(self, level):
        try:
            payload = {'level': str(level)}
            url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~memberDayPacketService~redPacketDraw'
            response = self.do_request(url, payload)
            if response and response.get('success'):
                coupon_names = [item['couponName'] for item in response.get('obj', [])] or []

                Log(f"🎁 会员日提取[{level}级]红包: {', '.join(coupon_names) or '空气'}")
            else:
                error_message = response.get('errorMessage') if response else "无返回"
                Log(f"📝 会员日提取[{level}级]红包失败: {error_message}")
                if "没有资格参与活动" in error_message:
                    self.memberDay_black = True
                    print("📝 会员日任务风控")
        except Exception as e:
            print(e)

    def exchange_coupon(self, coupon_amount, max_retries=3):
        """兑换指定面额的券"""
        self.getSign()
        exchange_headers = {
            'authority': 'mcs-mimp-web.sf-express.com',
            'origin': 'https://mcs-mimp-web.sf-express.com',
            'referer': 'https://mcs-mimp-web.sf-express.com/inboxPresentCouponList',
            'content-type': 'application/json;charset=UTF-8',
            'channel': 'wxwdsj',
            'sw8': '1-ZDRlNjQwZjUtNmViYi00NmRhLThiZTMtZWEyZTUzYTlhOWFm-ZDM4MjIzM2YtMDQ1NC00ZDJlLWIwMDUtYTQyZmE1ZGE4ZTI5-0-ZmI0MDgxNzA4NWJlNGUzOThlMGI2ZjRiMDgxNzc3NDY=-d2Vi-L2luYm94UHJlc2VudENvdXBvbkxpc3Q=-L21jcy1taW1wL2NvbW1vblBvc3Qvfm1lbWJlck5vbmAjdGl2aXR5fnJlY2VpdmVFeGNoYW5nZUdpZnRCYWdTZXJ2aWNlfmxpc3Q='
        }
        headers = {**self.headers, **exchange_headers}

        for attempt in range(1, max_retries + 1):
            try:
                list_url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~receiveExchangeGiftBagService~list'
                list_data = {"exchangeType": "EXCHANGE_SFC"}
                list_res = self.s.post(list_url, headers=headers, json=list_data, timeout=10)
                list_res.raise_for_status()
                list_json = list_res.json()
                
                if not list_json.get('success'):
                    return False, f"获取礼品列表失败"
                    
                coupon = next(
                    (g for g in list_json.get('obj', []) 
                    if coupon_amount in g.get('giftBagName', '')),
                    None
                )
                
                if not coupon:
                    return False, f"未找到{coupon_amount}券"
                    
                required_honey = coupon.get('exchangeHoney')
                if self.usableHoney < required_honey:
                    return False, f"丰蜜不足：需要{required_honey}，当前{self.usableHoney}"
                
                exchange_url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~receiveExchangeGiftBagService~exchange'
                exchange_data = {
                    "giftBagCode": coupon['giftBagCode'],
                    "ruleCode": coupon['ruleCode'],
                    "exchangeType": "EXCHANGE_SFC",
                    "memberNo": self.user_id,
                    "channel": "wxwdsj"
                }
                
                exchange_res = self.s.post(exchange_url, headers=headers, json=exchange_data, timeout=10)
                exchange_res.raise_for_status()
                exchange_json = exchange_res.json()
                
                if exchange_json.get('success'):
                    self.usableHoney -= required_honey
                    self.exchange_count += 1
                    return True, f"成功兑换{coupon_amount}券"
                else:
                    return False, exchange_json.get('errorMessage', '兑换失败')
                    
            except Exception as e:
                if attempt == max_retries:
                    return False, f"兑换异常：{str(e)}"
                time.sleep(2)
        
        return False, "多次尝试失败"

    def execute_exchange_range(self):
        """按照优先级执行兑换区间，支持连续兑换多张券"""
        Log(f"🎯 兑换目标：{' > '.join(self.target_amounts)}")
        Log(f"📊 最大兑换次数：{MAX_EXCHANGE_TIMES}")
        
        total_exchanged = 0
        exchange_results = []
        
        # 连续兑换，直到达到最大次数或无法继续兑换
        while total_exchanged < MAX_EXCHANGE_TIMES:
            exchanged_this_round = False
            
            # 按优先级尝试每种券
            for coupon_amount in self.target_amounts:
                if total_exchanged >= MAX_EXCHANGE_TIMES:
                    break
                    
                Log(f"💰 尝试兑换第{total_exchanged + 1}张 {coupon_amount} 券...")
                success, message = self.exchange_coupon(coupon_amount)
                
                if success:
                    Log(f"🎉 {message} (总计已兑换{self.exchange_count}张)")
                    exchange_results.append(coupon_amount)
                    total_exchanged += 1
                    exchanged_this_round = True
                    time.sleep(3)  # 兑换成功后等待3秒
                    break  # 成功兑换一张后，重新开始优先级循环
                else:
                    Log(f"❌ {coupon_amount} - {message}")
            
            # 如果这一轮没有成功兑换任何券，说明无法继续兑换，退出循环
            if not exchanged_this_round:
                break
        
        # 总结兑换结果
        if exchange_results:
            Log(f"✅ 兑换完成！共兑换{len(exchange_results)}张券：{', '.join(exchange_results)}")
            return True
        else:
            Log("❌ 未能兑换任何券")
            return False

    def exchange_23_coupon(self):
        """兑换功能（兼容原方法名）"""
        return self.execute_exchange_range()

    def main(self):
        global one_msg
        wait_time = random.randint(1000, 3000) / 1000.0  
        time.sleep(wait_time)  
        one_msg = ''
        if not self.login_res: return False

        # 执行微信小程序签到
        self.sign()
        # 执行APP端签到
        self.sign_app()
        # 执行奖励补领
        self.receive_sign_rewards()
        
        self.superWelfare_receiveRedPacket()
        self.get_SignTaskList()
        self.get_SignTaskList(True)

        # self.get_honeyTaskListStart()
        # self.honey_indexData()
        # self.honey_indexData(True)

        # activity_end_date = get_quarter_end_date()
        # days_left = (activity_end_date - datetime.now()).days
        # if days_left == 0:
        #     message = f"⏰ 今天采蜜活动截止兑换还有{days_left}天，请及时进行兑换！！"
        #     Log(message)
        # else:
        #     message = f"⏰ 今天采蜜活动截止兑换还有{days_left}天，请及时进行兑换！！\n--------------------------------"
        #     Log(message)

        # if not self.is_last_day and self.force_exchange:
        #     Log(f"⚡ 强制兑换模式已开启，兑换目标：{' > '.join(self.target_amounts)}")
        #     exchange_success = self.exchange_23_coupon()
        #     if not exchange_success:
        #         Log("❌ 强制兑换失败，所有目标券都无法兑换")

        current_date = datetime.now().day
        if 26 <= current_date <= 28:
            self.member_day_index()
        else:
            print('⏰ 未到指定时间不执行会员日任务\n==================================\n')

        return True

def get_quarter_end_date():
    current_date = datetime.now()
    current_month = current_date.month
    current_year = current_date.year
    next_quarter_first_day = datetime(current_year, ((current_month - 1) // 3 + 1) * 3 + 1, 1)
    quarter_end_date = next_quarter_first_day - timedelta(days=1)

    return quarter_end_date


def is_activity_end_date(end_date):
    current_date = datetime.now().date()
    end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

    return current_date == end_date

def main():
    APP_NAME = '顺丰速运'
    ENV_NAME = 'sfsyUrl'
    local_script_name = os.path.basename(__file__)
    local_version = '2.1'
    
    print(f"==================================")
    print(f"🚚 {APP_NAME}脚本 v{local_version}")

    if not QL_CLIENT_ID or not QL_CLIENT_SECRET:
        print(f"❌ 错误：未配置青龙面板 Open API 密钥！")
        print(f"请在脚本开头的 QL_CLIENT_ID 和 QL_CLIENT_SECRET 变量中完成配置")
        return

    ql = QLManager()

    env_ids = ql.get_env_ids(ENV_NAME)
    
    if not env_ids:
        print(f"❌ 未在面板中找到启用的 {ENV_NAME} 变量")
        return

    print(f"📋 启用【智能提取CK+实时变量读取】模式，共检测到 {len(env_ids)} 个启用的环境变量")
    print(f"==================================")

    print(f"\n⚡[阶段一] 开始智能提取CK")
    temp_index = 0

    pre_env_ids = ql.get_env_ids(ENV_NAME)
    
    for env_id in pre_env_ids:
        latest_value, remarks = ql.get_env_details(env_id)
        if not latest_value: continue

        tokens =[t.strip() for t in latest_value.replace('\n', '&').split('&') if t.strip()]
        if not tokens: continue

        needs_update = False
        new_tokens =[]

        for sub_index, raw_token in enumerate(tokens):
            temp_index += 1
            check_token = unquote(raw_token)
            
            if 'sessionId=' in check_token and '_login_mobile_=' in check_token:
                print(f"✅ 账号 {temp_index} 检测到已是标准CK格式，跳过提取")
                new_tokens.append(raw_token)
            elif check_token.startswith(('http://', 'https://')):
                print(f"🔄 账号 {temp_index} 检测到 signurl，尝试提取标准CK...")
                try:
                    runner = RUN(raw_token, temp_index - 1, env_id, sub_index)
                    if runner.login_res and hasattr(runner, 'standard_cookie'):
                        print(f"✨ 提取成功！准备覆盖为标准CK格式")
                        new_tokens.append(runner.standard_cookie)
                        needs_update = True
                    else:
                        print(f"⚠️ 提取失败，保留原值")
                        new_tokens.append(raw_token)
                    time.sleep(random.randint(1, 2))
                except Exception as e:
                    print(f"⚠️ 账号 {temp_index} 提取异常: {e}")
                    new_tokens.append(raw_token)
            else:
                new_tokens.append(raw_token)
        
        if needs_update:
            new_env_value = '&'.join(new_tokens)
            if ql.update_env(env_id, ENV_NAME, new_env_value, remarks):
                print(f"🎉 成功同步提取后的标准CK至青龙面板！")
            else:
                print(f"❌ 同步至青龙面板失败！")
            
    print(f"\n✅ [阶段一] 智能提取CK结束")
    print(f"==================================")

    print(f"\n🚀[阶段二] 开始执行日常任务逻辑...")
    global_index = 0

    for env_id in env_ids:
        latest_value, _ = ql.get_env_details(env_id)
        
        if not latest_value:
            continue

        tokens =[t.strip() for t in latest_value.replace('\n', '&').split('&') if t.strip()]
        
        if not tokens:
            continue

        for sub_index, raw_token in enumerate(tokens): # 改叫 raw_token
            # 传原始数据进去，让 RUN 内部去解
            run_result = RUN(raw_token, global_index, env_id, sub_index).main()
            global_index += 1

if __name__ == '__main__':
    main()
