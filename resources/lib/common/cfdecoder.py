# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------------
# Cloudflare decoder
# --------------------------------------------------------------------------------

import re
import time
from decimal import Decimal

from resources.lib.common import tools


class Cloudflare:
    def __init__(self, response):
        self.timeout = 5
        self.domain = tools.urlparse(response["url"])[1]
        self.protocol = tools.urlparse(response["url"])[0]
        self.js_data = {}
        self.header_data = {}

        if not "var s,t,o,p,b,r,e,a,k,i,n,g,f" in response["data"] or "chk_jschl" in response["url"]:
            return

        try:
            self.js_data["auth_url"] = \
                re.compile('<form id="challenge-form" action="([^"]+)" method="get">').findall(response["data"])[0]
            self.js_data["params"] = {}
            self.js_data["params"]["jschl_vc"] = \
                re.compile('<input type="hidden" name="jschl_vc" value="([^"]+)"/>').findall(response["data"])[0]
            self.js_data["params"]["pass"] = \
                re.compile('<input type="hidden" name="pass" value="([^"]+)"/>').findall(response["data"])[0]
            var, self.js_data["value"] = \
                re.compile('var s,t,o,p,b,r,e,a,k,i,n,g,f[^:]+"([^"]+)":([^\n]+)};', re.DOTALL).findall(
                    response["data"])[0]
            self.js_data["op"] = re.compile(var + "([\+|\-|\*|\/])=([^;]+)", re.MULTILINE).findall(response["data"])
            self.js_data["wait"] = int(re.compile("\}, ([\d]+)\);", re.MULTILINE).findall(response["data"])[0]) / 1000
        except Exception as e:
            print(e)
            self.js_data = {}

        if "refresh" in response["headers"]:
            try:
                self.header_data["wait"] = int(response["headers"]["refresh"].split(";")[0])
                self.header_data["auth_url"] = response["headers"]["refresh"].split("=")[1].split("?")[0]
                self.header_data["params"] = {}
                self.header_data["params"]["pass"] = response["headers"]["refresh"].split("=")[2]
            except Exception as e:
                print(e)
                self.header_data = {}

    @property
    def wait_time(self):
        if self.js_data.get("wait", 0):
            return self.js_data["wait"]
        else:
            return self.header_data.get("wait", 0)

    @property
    def is_cloudflare(self):
        return self.header_data.get("wait", 0) > 0 or self.js_data.get("wait", 0) > 0

    def get_url(self):
        # Metodo #1 (javascript)
        if self.js_data.get("wait", 0):
            jschl_answer = self.decode2(self.js_data["value"])

            for op, v in self.js_data["op"]:
                # jschl_answer = eval(str(jschl_answer) + op + str(self.decode2(v)))
                if op == '+':
                    jschl_answer = jschl_answer + self.decode2(v)
                elif op == '-':
                    jschl_answer = jschl_answer - self.decode2(v)
                elif op == '*':
                    jschl_answer = jschl_answer * self.decode2(v)
                elif op == '/':
                    jschl_answer = jschl_answer / self.decode2(v)

            self.js_data["params"]["jschl_answer"] = round(jschl_answer, 10) + len(self.domain)

            response = "%s://%s%s?%s" % (
                self.protocol, self.domain, self.js_data["auth_url"], tools.urlencode(self.js_data["params"]))

            time.sleep(self.js_data["wait"])

            return response

        # Metodo #2 (headers)
        if self.header_data.get("wait", 0):
            response = "%s://%s%s?%s" % (
                self.protocol, self.domain, self.header_data["auth_url"], tools.urlencode(self.header_data["params"]))

            time.sleep(self.header_data["wait"])

            return response

    def decode2(self, data):
        data = re.sub("\!\+\[\]", "1", data)
        data = re.sub("\!\!\[\]", "1", data)
        data = re.sub("\[\]", "0", data)

        pos = data.find("/")
        numerador = data[:pos]
        denominador = data[pos + 1:]

        aux = re.compile('\(([0-9\+]+)\)').findall(numerador)
        num1 = ""
        for n in aux:
            num1 += str(eval(n))

        aux = re.compile('\(([0-9\+]+)\)').findall(denominador)
        num2 = ""
        for n in aux:
            num2 += str(eval(n))

        # return float(num1) / float(num2)
        # return Decimal(Decimal(num1) / Decimal(num2)).quantize(Decimal('.0000000000000001'), rounding=ROUND_UP)
        return Decimal(Decimal(num1) / Decimal(num2)).quantize(Decimal('.0000000000000001'))

    def decode(self, data):
        t = time.time()
        timeout = False

        while not timeout:
            data = re.sub("\[\]", "''", data)
            data = re.sub("!\+''", "+1", data)
            data = re.sub("!''", "0", data)
            data = re.sub("!0", "1", data)

            if "(" in data:
                x, y = data.rfind("("), data.find(")", data.rfind("(")) + 1
                part = data[x + 1:y - 1]
            else:
                x = 0
                y = len(data)
                part = data

            val = ""

            if not part.startswith("+"): part = "+" + part

            for i, ch in enumerate(part):
                if ch == "+":
                    if not part[i + 1] == "'":
                        if val == "": val = 0
                        if type(val) == str:
                            val = val + self.get_number(part, i + 1)
                        else:
                            val = val + int(self.get_number(part, i + 1))
                    else:
                        val = str(val)
                        val = val + self.get_number(part, i + 1) or "0"

            if type(val) == str: val = "'%s'" % val
            data = data[0:x] + str(val) + data[y:]

            timeout = time.time() - t > self.timeout

            if not "+" in data and not "(" in data and not ")" in data:
                return int(self.get_number(data))

    def get_number(self, str, start=0):
        ret = ""
        for chr in str[start:]:
            try:
                int(chr)
            except:
                if ret: break
            else:
                ret += chr
        return ret
