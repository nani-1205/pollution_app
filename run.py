from app import create_app

app = create_app()

if __name__ == '__main__':
    # Use host='0.0.0.0' to make it accessible on your network
    # Debug mode should be False in production
    app.run(host='0.0.0.0', port=5000, debug=app.config.get('DEBUG', False))