# session_utils.py
import browser_cookie3
import requests

def get_authenticated_session(browser='firefox', domain='ifdian.net'):
    if browser.lower() == 'firefox':
        cj = browser_cookie3.firefox(domain_name=domain)
    elif browser.lower() == 'chrome':
        cj = browser_cookie3.chrome(domain_name=domain)
    else:
        raise ValueError('Unsupported browser')
    session = requests.Session()
    session.cookies.update(cj)
    return session