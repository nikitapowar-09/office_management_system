from app import app, db
from werkzeug.security import generate_password_hash
from models import User, Admin  # Adjust to your app's import paths

with app.app_context():
    # Hash the password securely
    hashed_password = generate_password_hash("Nikita@09")

    # Create the user with admin role
    new_user = User(username="admin", email="nikitapowar09@gmail.com", password_hash=hashed_password, role="admin")

    # Add the new user to the session and commits
    db.session.add(new_user)
    db.session.commit()

    # Create the admin, associating it with the new user
    new_admin = Admin(user_id=new_user.user_id, username="admin", email="nikitapowar09@gmail.com")

    # Add the new admin to the session and commit
    db.session.add(new_admin)
    db.session.commit()

    print("Admin user created successfully!")
