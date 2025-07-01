import requests

BASE_URL = "https://jsonplaceholder.typicode.com"


def get_posts(user_id=None):
    url = f"{BASE_URL}/posts"
    params = {'userId': user_id} if user_id else {}

    response = requests.get(url, params=params)
    response.raise_for_status()  # Raises error if the request failed

    posts = response.json()
    print(f"Retrieved {len(posts)} post(s):\n")
    for post in posts[:5]:  # Show only first 5
        print(f"Post #{post['id']} - {post['title']}")
        print(f"{post['body']}\n")


if __name__ == "__main__":
    get_posts(user_id=1)
    