from flask import Flask, render_template

app = Flask(__name__)

# The ONLY job of your Python backend now is to serve the 
# beautiful macOS interface. Google Firebase handles the rest.
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
