from flask import Flask, render_template

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return render_template("home.html")  # Changed to home.html

@app.route('/blog', methods=['GET'])
def blog():
    return render_template("blog.html")

@app.route('/write', methods=['GET'])
def write():
    return render_template("write.html")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5001, debug=True)
