import random
import re
import requests
import dns.resolver

# DNS and HTTP lists
dns_queries = [
    ("myip.opendns.com", "resolver1.opendns.com"),
    ("myip.opendns.com", "resolver2.opendns.com"),
    ("myip.opendns.com", "resolver3.opendns.com"),
    ("myip.opendns.com", "resolver4.opendns.com"),
    ("whoami.akamai.net", "ns1-1.akamaitech.net")
]

httplist = [
    "http://alma.ch/myip.cgi",
    "http://api.infoip.io/ip",
    "http://api.ipify.org",
    "http://bot.whatismyipaddress.com",
    "http://canhazip.com",
    "http://checkip.amazonaws.com",
    "http://eth0.me",
    "http://icanhazip.com",
    "http://ident.me",
    "http://ipecho.net/plain",
    "http://ipinfo.io/ip",
    "http://ipof.in/txt",
    "http://ip.tyk.nu",
    "http://l2.io/ip",
    "http://smart-ip.net/myip",
    "http://wgetip.com",
    "http://whatismyip.akamai.com"
]

# Function to validate IP
def valid_ip(ip):
    return re.match(r'^\d{1,3}(\.\d{1,3}){3}$', ip) is not None

# Function to shuffle lists
def shuffle_list(lst):
    random.shuffle(lst)
    return lst

# Function to get IP using DNS
def get_ip_dns():
    for query, server in shuffle_list(dns_queries):
        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = [dns.resolver.resolve(server, 'A')[0].address]
            answers = resolver.resolve(query, 'A')
            for rdata in answers:
                ip = rdata.address
                if valid_ip(ip):
                    return ip
        except (dns.exception.DNSException, IndexError):
            continue
    return None

# Function to get IP using HTTP
def get_ip_http():
    for url in shuffle_list(httplist):
        try:
            response = requests.get(url, timeout=2)
            ip = response.text.strip()
            if valid_ip(ip):
                return ip
        except requests.RequestException:
            continue
    return None

# Main function to get IP
def get_external_ip():
    ip = get_ip_dns()
    if ip is None:
        ip = get_ip_http()
        if ip is None:
            ip = "n/a"
    return ip

if __name__ == '__main__':
    print(get_external_ip())
