"""
main.py
Poora pipeline yahin se chalता hai. GitHub Actions daily isi file ko run karega.

Flow (har naye job ke liye, ek ek karke):
  1. fetch_jobs.py       -> naye jobs nikalo (jo pehle post nahi hui)
  2. generate_creative.py -> image ya reel banao (alternately)
  3. git commit+push      -> docs/media me daalo taaki GitHub Pages se public URL mile
  4. instagram_post.py    -> Graph API se Instagram pe publish karo
  5. state.py              -> job ko "posted" mark karo taaki dubara na ho
"""

import os
import subprocess
import sys
import time

import requests

import config
import fetch_jobs
import generate_creative
import instagram_post
import state


def git_commit_and_push(paths, message):
    subprocess.run(["git", "add", *paths], check=True)
    # agar kuch change hi nahi hai to commit skip karo
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if diff.returncode == 0:
        return False
    subprocess.run(["git", "-c", "user.name=job-bot", "-c", "user.email=job-bot@users.noreply.github.com",
                     "commit", "-m", message], check=True)
    subprocess.run(["git", "push"], check=True)
    return True


def wait_until_public(url, max_wait=180, poll_every=10):
    """GitHub Pages update hone me thoda time leta hai, ready hone tak poll karo."""
    waited = 0
    while waited < max_wait:
        try:
            resp = requests.head(url, timeout=15)
            if resp.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(poll_every)
        waited += poll_every
    return False


def main():
    if not config.GITHUB_PAGES_BASE_URL:
        print("ERROR: GITHUB_PAGES_BASE_URL set nahi hai. README ka setup step dekho.")
        sys.exit(1)

    jobs = fetch_jobs.fetch_all_jobs()
    if not jobs:
        print("Koi job data nahi mila (sheet/API check karo). Exiting.")
        return

    posted_ids = state.load_posted_ids()
    new_jobs = [j for j in jobs if j["id"] not in posted_ids][:config.MAX_POSTS_PER_RUN]

    if not new_jobs:
        print("Koi naya job nahi hai post karne ke liye.")
        return

    print(f"{len(new_jobs)} naye jobs post honge is run me.")

    for i, job in enumerate(new_jobs):
        use_reel = (i % 2 == 0)  # alternate: reel, image, reel, image...
        caption = generate_creative.build_caption(job)

        try:
            if use_reel:
                local_path = os.path.join(config.MEDIA_DIR, f"{job['id']}.mp4")
                generate_creative.build_reel(job, local_path)
                public_url = f"{config.GITHUB_PAGES_BASE_URL}/media/{job['id']}.mp4"
            else:
                local_path = os.path.join(config.MEDIA_DIR, f"{job['id']}.jpg")
                generate_creative.build_image(job, local_path)
                public_url = f"{config.GITHUB_PAGES_BASE_URL}/media/{job['id']}.jpg"

            pushed = git_commit_and_push([local_path], f"Add media for job {job['id']}")
            if pushed:
                print(f"Waiting for GitHub Pages to serve {public_url} ...")
                ready = wait_until_public(public_url)
                if not ready:
                    print(f"WARNING: {public_url} abhi tak public nahi hua, phir bhi try kar rahe hain.")

            if use_reel:
                media_id = instagram_post.post_reel(public_url, caption)
            else:
                media_id = instagram_post.post_image(public_url, caption)

            print(f"Posted job {job['id']} ({job['title']} @ {job['company']}) -> media_id {media_id}")
            state.mark_posted(job["id"])

        except Exception as e:
            print(f"FAILED to post job {job['id']}: {e}")
            # is job ko skip karke agli job try karo, state update nahi hoga isliye next run me retry hoga

        if i < len(new_jobs) - 1:
            time.sleep(config.POST_GAP_SECONDS)


if __name__ == "__main__":
    main()
