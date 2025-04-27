import requests
import re
import json
from urllib.parse import urljoin
from datetime import datetime

# import pandas as pd


class XYZRankScraper:
    def __init__(self):
        self.base_url = "https://xyzrank.com"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Referer": self.base_url,
            }
        )
        self.log = []

    def log_message(self, message):
        """记录日志信息"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        self.log.append(log_entry)

    def get_current_js_url(self):
        """获取当前最新的JS文件URL"""
        try:
            self.log_message("正在获取首页HTML...")
            response = self.session.get(self.base_url, timeout=15)
            response.raise_for_status()

            # 精确匹配JS文件URL
            js_pattern = r'<script\s+[^>]*?src=["\'](https?://[^"\']+?/assets/index\.[a-f0-9]+\.js)["\']'
            match = re.search(js_pattern, response.text)

            if not match:
                # 尝试匹配相对路径
                js_pattern_rel = (
                    r'<script\s+[^>]*?src=["\'](/assets/index\.[a-f0-9]+\.js)["\']'
                )
                match = re.search(js_pattern_rel, response.text)
                if match:
                    js_url = urljoin(self.base_url, match.group(1))
                    self.log_message(f"找到JS文件(相对路径): {js_url}")
                    return js_url

                raise ValueError("无法在页面中找到JS文件URL")

            js_url = match.group(1)
            self.log_message(f"找到JS文件: {js_url}")
            return js_url

        except Exception as e:
            self.log_message(f"获取JS文件URL失败: {str(e)}")
            return None

    def extract_json_urls(self, js_url):
        """从JS文件中提取JSON文件URL - 精确匹配特定格式"""
        try:
            self.log_message(f"正在下载JS文件: {js_url}")
            response = self.session.get(js_url, timeout=20)
            response.raise_for_status()
            js_content = response.text

            # 精确匹配您提供的格式: const pI="...",gI="...",mI="...",_I="..."
            json_pattern = r'const\s+\w+\s*=\s*"([^"]+\.json)"\s*,\s*\w+\s*=\s*"([^"]+\.json)"\s*,\s*\w+\s*=\s*"([^"]+\.json)"\s*,\s*\w+\s*=\s*"([^"]+\.json)"'
            match = re.search(json_pattern, js_content)

            if not match:
                raise ValueError("无法匹配JSON文件URL的特定格式")

            json_urls = list(match.groups())
            self.log_message(f"成功提取4个JSON文件URL: {json_urls}")
            return json_urls

        except Exception as e:
            self.log_message(f"从JS文件提取JSON URL失败: {str(e)}")
            return None

    def download_json_data(self, json_url):
        """下载并解析JSON数据"""
        try:
            self.log_message(f"正在下载JSON文件: {json_url}")
            response = self.session.get(json_url, timeout=20)
            response.raise_for_status()

            # 验证内容类型
            content_type = response.headers.get("Content-Type", "")
            if "application/json" not in content_type:
                self.log_message(f"警告: {json_url} 的Content-Type不是application/json")

            data = response.json()
            self.log_message(f"成功下载JSON文件: {json_url}")
            return data
        except Exception as e:
            self.log_message(f"下载JSON数据失败({json_url}): {str(e)}")
            return None

    def save_data(self, data, json_type):
        """保存数据到文件"""
        # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 确定文件类型
        type_mapping = {
            "full.": "full",
            "new-podcasts.": "new_podcasts",
            "hot-episodes.": "hot_episodes",
            "hot-episodes-new.": "hot_episodes_new",
        }

        prefix = None
        for k, v in type_mapping.items():
            if k in json_type:
                prefix = v
                break

        if not prefix:
            prefix = json_type.split("/")[-1].split(".")[0]

        # 保存为JSON
        json_filename = f"{prefix}.json"
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.log_message(f"已保存JSON: {json_filename}")

        # 保存为CSV
        # csv_filename = f"xyzrank_{prefix}_{timestamp}.csv"
        # try:
        #     if isinstance(data, list):
        #         df = pd.DataFrame(data)
        #     elif isinstance(data, dict):
        #         df = pd.DataFrame([data])
        #     else:
        #         raise ValueError("不支持的数据类型")

        #     df.to_csv(csv_filename, index=False, encoding="utf-8-sig")
        #     self.log_message(f"已保存CSV: {csv_filename}")
        # except Exception as e:
        #     self.log_message(f"保存CSV失败({prefix}): {str(e)}")

    def run(self):
        """执行完整爬取流程"""
        self.log_message("开始XYZRank数据爬取流程")

        # 1. 获取JS文件URL
        js_url = self.get_current_js_url()
        if not js_url:
            self.log_message("流程终止: 无法获取JS文件URL")
            return False

        # 2. 提取所有JSON文件URL
        json_urls = self.extract_json_urls(js_url)
        if not json_urls or len(json_urls) != 4:
            self.log_message("流程终止: 无法提取完整的JSON文件URL")
            return False

        # 3. 下载并保存所有JSON数据
        success = True
        for json_url in json_urls:
            data = self.download_json_data(json_url)
            if data:
                self.save_data(data, json_url)
            else:
                success = False

        # 保存日志
        # with open("xyzrank_scraper_log.txt", "w", encoding="utf-8") as f:
        #     f.write("\n".join(self.log))

        return success


if __name__ == "__main__":
    scraper = XYZRankScraper()
    success = scraper.run()

    if not success:
        print("爬取过程中出现错误，请检查日志文件 xyzrank_scraper_log.txt")
    else:
        print("所有JSON文件下载完成！")
