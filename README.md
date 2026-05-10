# 爱发电播客下载
**前排提醒：本工具仅能下载正在发电的节目**
## 使用
注意：有可能需要`ffmpeg`
```shell
$ git clone git@github.com:senventise/afdian_podcast_down.git
$ cd afdian_podcast_down
$ pip install -r requirements.txt
```
### 获取 album_id  
节目的url应为：`https://afdian.net/album/ALBUM_ID`。
注意：是 节目专辑的 URL，不是创作者主页。
### cookie 自动读取 
本工具使用浏览器登录态自动读取 cookies，无需手动配置 auth_token

支持 Firefox 或 Chrome 浏览器
工具会自动读取浏览器 cookie 并保持登录状态
不需要 Cookie-Editor 或 config.ini

### 下载全部
```shell
$ python main.py --id ALBUM_ID
```
或者
```shell
$ python main.py --url https://ifdian.net/album/1234567890abcdef
```
### 下载最新n期
```shell
# 列出最新n期
$ python main.py --id ALBUM_ID --latest n --list
# 下载
$ python main.py --id ALBUM_ID --latest n
```
或者
```shell
# 列出最新n期
$ python main.py --url https://ifdian.net/album/1234567890abcdef --latest n --list
# 下载
$ python main.py --url https://ifdian.net/album/1234567890abcdef --latest n
```

### 其他说明
文件名会自动处理非法字符
下载过程会自动嵌入封面和作者信息
支持随机 sleep 防止请求过快
全局 session 自动带 cookie 和 referer，无需额外配置