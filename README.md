# 爱发电播客下载
**前排提醒：本工具仅能下载当前账号正在发电、且有权限访问的节目。**

本工具用于下载爱发电专辑中的音频内容，并自动写入标题、作者、封面等基础 ID3 信息。

当前支持：

- 专辑 URL：`https://ifdian.net/album/ALBUM_ID`
- 单条节目 URL：`https://ifdian.net/p/POST_ID`
- 自动读取 Firefox / Chrome 浏览器登录态 cookies
- 下载全部专辑内容
- 下载最新 n 期
- 仅列出节目内容
- 自动处理文件名非法字符
- 自动嵌入封面、作者、标题、简介等信息
- 随机 sleep，降低请求过快风险

## 前置说明

注意：部分音频可能需要 `ffmpeg` 转码。

如果遇到音频格式无法被 `eyed3` 识别，工具会尝试调用本机 `ffmpeg` 进行转换。因此建议提前安装并确保 `ffmpeg` 可在命令行中直接调用。

```shell
ffmpeg -version
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
如需指定 Chrome：
```shell
python main.py --url https://ifdian.net/album/1234567890abcdef --browser chrome
```
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
### 下载单条节目
部分节目链接不是专辑页，而是单条节目页，例如：
```
https://ifdian.net/p/abcdefg1234567890abcdef
```
这类链接可以直接传给 --url：
```shell
$ python main.py --url https://ifdian.net/p/abcdefg1234567890abcdef
```
单条节目默认会下载到
```
single_posts/
```

### 其他说明
文件名会自动处理 Windows / Linux / macOS 中的非法字符。
下载过程会自动嵌入封面、作者、标题和简介。
全局 session 会自动携带浏览器 cookie 和 referer。
专辑批量下载时会在每条之间随机 sleep，避免请求过快。
单条 /p/ 节目下载完成后不会额外等待。
如果浏览器 cookies 失效，请重新在浏览器中打开爱发电并刷新登录状态后再运行工具。