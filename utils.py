import os
import csv
import requests
from dotenv import load_dotenv
from openai import OpenAI
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods.posts import EditPost, GetPost

load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize WordPress XML-RPC client
wp_client = Client(
    os.getenv("WORDPRESS_XMLRPC_URL"),  # this should be like https://your-site.com/xmlrpc.php
    os.getenv("WORDPRESS_USERNAME"),
    os.getenv("WORDPRESS_PASSWORD")
)

def process_csv(csv_data):
    report = ""
    reader = csv.reader(csv_data.splitlines())
    next(reader, None)  # skip header
    for row in reader:
        if len(row) < 2:
            continue
        url = row[0].strip()
        keywords = [k.strip() for k in row[1].split(",")]
        if not url.startswith("http"):
            report += f"❌ Invalid URL '{url}'\n"
            continue
        try:
            print(f"🔍 Processing {url}")
            post_id, post_content = get_post_id_from_url(url)
            # print(post_content)
            optimized = optimize_content(post_content, keywords)
            update_wordpress(post_id, optimized)
            report += f"✅ Updated {url}\n"
        except Exception as e:
            report += f"❌ Failed {url}: {e}\n"
    return report

def get_post_id_from_url(url):
    slug = url.rstrip("/").split("/")[-1]
    wp_rest_api_base = os.getenv("WORDPRESS_REST_URL").rstrip("/") + "/wp-json/wp/v2"

    response = requests.get(f"{wp_rest_api_base}/posts?slug={slug}")
    response.raise_for_status()
    data = response.json()
    if not data:
        raise ValueError(f"No post found with slug '{slug}'")
    post_id = data[0]['id']
    post_content = data[0]['content']['rendered']  # Raw content: data[0]['content']['raw']
    
    return post_id, post_content


def optimize_content(content, keywords):
    prompt = f"""
Rewrite the following blog post to better target the keywords: {', '.join(keywords)}.

Blog Post:
{content}

Goal: Improve rankings and engagement for these keywords
Instructions:

1. Do a content gap analysis vs top 3 ranking competitors.

2. Suggest content enhancements/additions based on the gaps.

3. Highlight all new or enhanced content in yellow background (e.g., using ==highlight==).

4. DO NOT alter or remove existing internal links.

5. Keep tone consistent with the existing site tone (Australian, friendly, expert).

6. Deliver the enhanced content in a copy-paste ready format.
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert SEO blog writer."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=2048
    )
    return response.choices[0].message.content

def update_wordpress(post_id, new_content):
    post = wp_client.call(GetPost(post_id))
    post.content = new_content
    wp_client.call(EditPost(post_id, post))

from datetime import datetime

def update_wordpress_test(post_id, new_content):
    # Get current date and time in a readable format
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Append the timestamp to the new content
    updated_content = f"{new_content}\n\n<em>Last updated: {current_time}</em>"

    print("Updated content")
    print(updated_content)
    
    # Fetch and update the post
    post = wp_client.call(GetPost(post_id))
    post.content = updated_content
    wp_client.call(EditPost(post_id, post))