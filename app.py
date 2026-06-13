import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for

from . import config
from .task_manager import create_task, get_task, list_tasks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/")
def index():
    """Home page — B站链接输入"""
    recent = list_tasks()[:10]
    return render_template("index.html", recent=recent)


@app.route("/submit", methods=["POST"])
def submit():
    """Submit a Bilibili URL for processing."""
    url = request.form.get("url", "").strip()
    if not url:
        return render_template("index.html", error="请输入 B 站视频链接")
    if "bilibili.com" not in url and "b23.tv" not in url:
        return render_template("index.html", error="请输入有效的 B 站链接")
    task_id = create_task(url)
    return redirect(url_for("processing", task_id=task_id))


@app.route("/processing/<task_id>")
def processing(task_id):
    """Processing progress page."""
    task = get_task(task_id)
    if task is None:
        return redirect(url_for("index"))
    if task["status"] == "done":
        return redirect(url_for("result", task_id=task_id))
    if task["status"] == "error":
        return redirect(url_for("result", task_id=task_id))
    return render_template("processing.html", task_id=task_id)


@app.route("/status/<task_id>")
def status(task_id):
    """API endpoint — return task status as JSON for polling."""
    task = get_task(task_id)
    if task is None:
        return jsonify({"status": "not_found"})
    return jsonify({
        "id": task["id"],
        "status": task["status"],
        "progress": task["progress"],
        "message": task["message"],
        "title": task.get("title", ""),
    })


@app.route("/result/<task_id>")
def result(task_id):
    """Result page — show transcript and notes."""
    task = get_task(task_id)
    if task is None:
        return redirect(url_for("index"))
    return render_template(
        "result.html",
        title=task.get("title", ""),
        status=task["status"],
        error=task.get("error", ""),
        segments=task.get("segments", []),
        full_text=task.get("full_text", ""),
        polished_text=task.get("polished_text", ""),
        notes=task.get("notes", ""),
        task_id=task_id,
    )


@app.route("/api/text/<task_id>")
def api_text(task_id):
    """API endpoint — return raw transcript text."""
    task = get_task(task_id)
    if task is None:
        return jsonify({"error": "not_found"}), 404
    return jsonify({
        "full_text": task.get("full_text", ""),
        "polished_text": task.get("polished_text", ""),
        "notes": task.get("notes", ""),
    })


if __name__ == "__main__":
    logger.info("Starting BiliSum on %s:%s", config.HOST, config.PORT)
    app.run(host=config.HOST, port=config.PORT, debug=False)
