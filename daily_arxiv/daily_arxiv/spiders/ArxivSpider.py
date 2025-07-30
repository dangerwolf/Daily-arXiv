import scrapy
import os
import json
import urllib.parse
from scrapy.selector import Selector

class ArxivSpider(scrapy.Spider):
    name = "ArxivSpider"
    allowed_domains = ["arxiv.org"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.search_terms = os.environ.get("SEARCH_TERMS", "fraud detection").split(",")
        self.search_terms = [term.strip() for term in self.search_terms if term.strip()]
        self.seen_ids_file = ".cache/seen.json"
        os.makedirs(".cache", exist_ok=True)

        if os.path.exists(self.seen_ids_file):
            with open(self.seen_ids_file, "r", encoding="utf-8") as f:
                self.seen_ids = set(json.load(f))
        else:
            self.seen_ids = set()

        # 构建 advanced search URL
        base = "https://arxiv.org/search/advanced?"
        params = {
            "advanced": "",
            "classification-computer_science": "y",
            "classification-physics_archives": "all",
            "classification-include_cross_list": "include",
            "date-filter_by": "all_dates",
            "abstracts": "show",
            "size": "200",
            "order": "-submitted_date",
        }

        for i, term in enumerate(self.search_terms):
            params[f"terms-{i}-operator"] = "OR" if i > 0 else "AND"
            params[f"terms-{i}-term"] = term
            params[f"terms-{i}-field"] = "all"

        self.start_urls = [base + urllib.parse.urlencode(params)]

    def parse(self, response):
        selector = Selector(response)
        papers = selector.css("li.arxiv-result")

        new_ids = []

        for paper in papers:
            id_link = paper.css("p.list-title a::attr(href)").get()
            if not id_link:
                continue
            arxiv_id = id_link.strip().split("/")[-1]

            if arxiv_id in self.seen_ids:
                self.logger.debug(f"Skip seen: {arxiv_id}")
                continue

            title = paper.css("p.title::text").get()
            if title:
                title = title.strip()

            yield {
                "id": arxiv_id,
                "title": title,
                "url": id_link.strip(),
            }

            self.logger.info(f"Found new paper: {arxiv_id}")
            new_ids.append(arxiv_id)

        # 保存更新后的 seen_ids
        self.seen_ids.update(new_ids)
        with open(self.seen_ids_file, "w", encoding="utf-8") as f:
            json.dump(sorted(list(self.seen_ids)), f, indent=2)
