from charon import app

@app.route("/")
@app.route("/index")
def hello():
    return "Hello World!"

if __name__ == "__main__":
    app.run()
