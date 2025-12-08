from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from config import Config
from models import db, User, File, LogBook, FilePermission
from storage import get_storage_backend
import os
import io
import zipfile
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

storage_backend = get_storage_backend(app.config)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def log_action(action, details=None):
    if current_user.is_authenticated:
        log_entry = LogBook(user_id=current_user.id, action=action, details=details, ip_address=request.remote_addr)
        db.session.add(log_entry)
        db.session.commit()


def can_access_file(file, permission_type='read'):
    """Check if current user can access a file with given permission.
    
    Args:
        file: File model instance
        permission_type: 'read', 'write', or 'delete'
    
    Returns:
        bool: True if user has permission
    """
    # Owner has full access
    if file.user_id == current_user.id:
        return True
    
    # Admin has full access
    if current_user.role == 'admin':
        return True
    
    # Check shared permissions
    permission = FilePermission.query.filter_by(
        file_id=file.id,
        user_id=current_user.id
    ).first()
    
    if not permission:
        return False
    
    if permission_type == 'read':
        return permission.can_read
    elif permission_type == 'write':
        return permission.can_write
    elif permission_type == 'delete':
        return permission.can_delete
    
    return False

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        if not username or not email or not password:
            flash('All fields are required', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            log_action('login', f'User {username} logged in')
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    log_action('logout', f'User {current_user.username} logged out')
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    files = File.query.filter_by(user_id=current_user.id).order_by(File.upload_date.desc()).all()
    recent_logs = LogBook.query.filter_by(user_id=current_user.id).order_by(LogBook.timestamp.desc()).limit(10).all()
    return render_template('dashboard.html', files=files, logs=recent_logs)

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        flash('No file selected', 'danger')
        return redirect(url_for('dashboard'))
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('dashboard'))
    if file and allowed_file(file.filename):
        original_filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{original_filename}"
        
        # Read file content into memory to get size and allow multiple reads
        file_content = file.read()
        file_size = len(file_content)
        file.stream = io.BytesIO(file_content)
        file.stream.seek(0)
        
        existing_file = File.query.filter_by(user_id=current_user.id, original_filename=original_filename).order_by(File.version.desc()).first()
        version = existing_file.version + 1 if existing_file else 1
        try:
            storage_result = storage_backend.save(file, filename, current_user.id)
        except RuntimeError as exc:
            flash(str(exc), 'danger')
            return redirect(url_for('dashboard'))
        new_file = File(
            filename=filename,
            original_filename=original_filename,
            file_size=file_size,
            file_path=storage_result.key,
            version=version,
            user_id=current_user.id,
        )
        db.session.add(new_file)
        db.session.commit()
        log_action('upload', f'Uploaded {original_filename} (v{version}, {file_size} bytes)')
        flash(f'File uploaded successfully! Version {version}', 'success')
    else:
        flash('File type not allowed', 'danger')
    return redirect(url_for('dashboard'))


@app.route('/upload-multiple', methods=['POST'])
@login_required
def upload_files():
    """Handle multiple file uploads."""
    if 'files' not in request.files:
        flash('No files selected', 'danger')
        return redirect(url_for('dashboard'))
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        flash('No files selected', 'danger')
        return redirect(url_for('dashboard'))
    
    uploaded_count = 0
    failed_count = 0
    
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            filename = f"{timestamp}_{original_filename}"
            
            # Read file content into memory
            file_content = file.read()
            file_size = len(file_content)
            file.stream = io.BytesIO(file_content)
            file.stream.seek(0)
            
            existing_file = File.query.filter_by(user_id=current_user.id, original_filename=original_filename).order_by(File.version.desc()).first()
            version = existing_file.version + 1 if existing_file else 1
            
            try:
                storage_result = storage_backend.save(file, filename, current_user.id)
                new_file = File(
                    filename=filename,
                    original_filename=original_filename,
                    file_size=file_size,
                    file_path=storage_result.key,
                    version=version,
                    user_id=current_user.id,
                )
                db.session.add(new_file)
                uploaded_count += 1
            except RuntimeError:
                failed_count += 1
        else:
            failed_count += 1
    
    db.session.commit()
    
    if uploaded_count > 0:
        log_action('bulk_upload', f'Uploaded {uploaded_count} files')
        flash(f'Successfully uploaded {uploaded_count} file(s)', 'success')
    if failed_count > 0:
        flash(f'{failed_count} file(s) failed to upload', 'warning')
    
    return redirect(url_for('dashboard'))


@app.route('/rename/<int:file_id>', methods=['POST'])
@login_required
def rename_file(file_id):
    """Rename a file."""
    file = File.query.get_or_404(file_id)
    
    if not can_access_file(file, 'write'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
    
    new_filename = request.form.get('new_filename', '').strip()
    if not new_filename:
        flash('Filename cannot be empty', 'danger')
        return redirect(url_for('dashboard'))
    
    new_filename = secure_filename(new_filename)
    if not new_filename:
        flash('Invalid filename', 'danger')
        return redirect(url_for('dashboard'))
    
    old_name = file.original_filename
    file.original_filename = new_filename
    db.session.commit()
    
    log_action('rename', f'Renamed "{old_name}" to "{new_filename}"')
    flash(f'File renamed to {new_filename}', 'success')
    return redirect(url_for('dashboard'))


@app.route('/thumbnail/<int:file_id>')
@login_required
def thumbnail(file_id):
    """Generate and serve thumbnail for image files."""
    file = File.query.get_or_404(file_id)
    
    if not can_access_file(file, 'read'):
        return '', 403
    
    ext = file.original_filename.rsplit('.', 1)[-1].lower()
    if ext not in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']:
        return '', 404
    
    try:
        file_content = storage_backend.get_file_content(file)
        if not file_content:
            return '', 404
        
        # Try to create thumbnail using PIL if available
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(file_content))
            img.thumbnail((80, 80))
            
            thumb_buffer = io.BytesIO()
            # Convert to RGB if necessary (for PNG with transparency)
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            img.save(thumb_buffer, format='JPEG', quality=70)
            thumb_buffer.seek(0)
            
            return send_file(thumb_buffer, mimetype='image/jpeg')
        except ImportError:
            # PIL not installed, serve original image
            return send_file(io.BytesIO(file_content), mimetype=f'image/{ext}')
    except Exception:
        return '', 404


@app.route('/preview/<int:file_id>')
@login_required
def preview_file_content(file_id):
    """Serve file content for preview."""
    file = File.query.get_or_404(file_id)
    
    if not can_access_file(file, 'read'):
        return '', 403
    
    ext = file.original_filename.rsplit('.', 1)[-1].lower()
    
    try:
        file_content = storage_backend.get_file_content(file)
        if not file_content:
            return '', 404
        
        # Determine MIME type
        mime_types = {
            'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
            'gif': 'image/gif', 'webp': 'image/webp', 'bmp': 'image/bmp',
            'pdf': 'application/pdf',
            'txt': 'text/plain', 'md': 'text/plain', 'csv': 'text/plain',
            'json': 'application/json', 'xml': 'text/xml',
            'html': 'text/html', 'css': 'text/css', 'js': 'text/javascript',
            'py': 'text/plain'
        }
        mime_type = mime_types.get(ext, 'application/octet-stream')
        
        return send_file(io.BytesIO(file_content), mimetype=mime_type)
    except Exception:
        return '', 404


@app.route('/download/<int:file_id>')
@login_required
def download_file(file_id):
    file = File.query.get_or_404(file_id)
    if not can_access_file(file, 'read'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
    log_action('download', f'Downloaded {file.original_filename} (v{file.version})')
    try:
        return storage_backend.download(file)
    except RuntimeError as exc:
        flash(str(exc), 'danger')
        return redirect(url_for('dashboard'))

@app.route('/delete/<int:file_id>', methods=['POST'])
@login_required
def delete_file(file_id):
    file = File.query.get_or_404(file_id)
    if not can_access_file(file, 'delete'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
    try:
        storage_backend.delete(file.file_path)
    except RuntimeError as exc:
        flash(str(exc), 'danger')
        return redirect(url_for('dashboard'))
    log_action('delete', f'Deleted {file.original_filename} (v{file.version})')
    db.session.delete(file)
    db.session.commit()
    flash('File deleted successfully', 'success')
    return redirect(url_for('dashboard'))


@app.route('/download-zip', methods=['POST'])
@login_required
def download_zip():
    """Download multiple files as a single ZIP archive."""
    file_ids = request.form.getlist('file_ids')
    if not file_ids:
        flash('No files selected', 'danger')
        return redirect(url_for('dashboard'))
    
    # Create in-memory ZIP file
    zip_buffer = io.BytesIO()
    files_added = []
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file_id in file_ids:
            try:
                file = File.query.get(int(file_id))
                if not file or not can_access_file(file, 'read'):
                    continue
                
                # Get file content from storage backend
                file_content = storage_backend.get_file_content(file)
                if file_content:
                    # Use versioned filename to avoid conflicts
                    archive_name = f"v{file.version}_{file.original_filename}"
                    zip_file.writestr(archive_name, file_content)
                    files_added.append(file.original_filename)
            except Exception as e:
                continue
    
    if not files_added:
        flash('No accessible files to download', 'danger')
        return redirect(url_for('dashboard'))
    
    zip_buffer.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    zip_filename = f"files_{timestamp}.zip"
    
    log_action('bulk_download', f'Downloaded ZIP with {len(files_added)} files: {", ".join(files_added)}')
    
    return send_file(
        zip_buffer,
        mimetype='application/zip',
        as_attachment=True,
        download_name=zip_filename
    )


@app.route('/share/<int:file_id>', methods=['GET', 'POST'])
@login_required
def share_file(file_id):
    """Share a file with another user with specific permissions."""
    file = File.query.get_or_404(file_id)
    
    # Only owner can share
    if file.user_id != current_user.id:
        flash('Only the file owner can share files', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        can_read = request.form.get('can_read') == 'on'
        can_write = request.form.get('can_write') == 'on'
        can_delete = request.form.get('can_delete') == 'on'
        
        target_user = User.query.filter_by(username=username).first()
        if not target_user:
            flash('User not found', 'danger')
            return redirect(url_for('share_file', file_id=file_id))
        
        if target_user.id == current_user.id:
            flash('Cannot share with yourself', 'danger')
            return redirect(url_for('share_file', file_id=file_id))
        
        # Update or create permission
        permission = FilePermission.query.filter_by(
            file_id=file.id,
            user_id=target_user.id
        ).first()
        
        if permission:
            permission.can_read = can_read
            permission.can_write = can_write
            permission.can_delete = can_delete
        else:
            permission = FilePermission(
                file_id=file.id,
                user_id=target_user.id,
                can_read=can_read,
                can_write=can_write,
                can_delete=can_delete,
                granted_by=current_user.id
            )
            db.session.add(permission)
        
        db.session.commit()
        log_action('share', f'Shared {file.original_filename} with {username} (R:{can_read}/W:{can_write}/D:{can_delete})')
        flash(f'File shared with {username}', 'success')
        return redirect(url_for('dashboard'))
    
    # GET: show sharing form
    existing_permissions = FilePermission.query.filter_by(file_id=file.id).all()
    return render_template('share.html', file=file, permissions=existing_permissions)


@app.route('/shared-with-me')
@login_required
def shared_with_me():
    """View files shared with the current user."""
    permissions = FilePermission.query.filter_by(user_id=current_user.id).all()
    shared_files = [(p.file, p) for p in permissions if p.file]
    return render_template('shared.html', shared_files=shared_files)

@app.route('/logs')
@login_required
def view_logs():
    logs = LogBook.query.filter_by(user_id=current_user.id).order_by(LogBook.timestamp.desc()).all()
    return render_template('logs.html', logs=logs)


# ==================== ADMIN FEATURES ====================

def admin_required(f):
    """Decorator to restrict access to admin users only."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard with system overview."""
    users = User.query.all()
    files = File.query.all()
    logs = LogBook.query.order_by(LogBook.timestamp.desc()).limit(50).all()
    
    # Statistics
    total_users = len(users)
    total_files = len(files)
    total_size = sum(f.file_size for f in files)
    total_size_mb = total_size / (1024 * 1024)
    
    return render_template('admin/dashboard.html', 
                           users=users, 
                           files=files, 
                           logs=logs,
                           total_users=total_users,
                           total_files=total_files,
                           total_size_mb=total_size_mb)


@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    """Manage all users."""
    users = User.query.all()
    return render_template('admin/users.html', users=users)


@app.route('/admin/users/<int:user_id>/toggle-role', methods=['POST'])
@login_required
@admin_required
def toggle_user_role(user_id):
    """Toggle user role between admin and user."""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Cannot change your own role', 'danger')
    else:
        user.role = 'user' if user.role == 'admin' else 'admin'
        db.session.commit()
        log_action('admin_role_change', f'Changed {user.username} role to {user.role}')
        flash(f'User {user.username} is now {user.role}', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    """Delete a user and all their files."""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Cannot delete yourself', 'danger')
    else:
        # Delete user's files from storage
        for file in user.files:
            try:
                storage_backend.delete(file.file_path)
            except:
                pass
        username = user.username
        db.session.delete(user)
        db.session.commit()
        log_action('admin_delete_user', f'Deleted user {username} and all their files')
        flash(f'User {username} deleted', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/files')
@login_required
@admin_required
def admin_files():
    """View all files in the system."""
    files = File.query.order_by(File.upload_date.desc()).all()
    return render_template('admin/files.html', files=files)


@app.route('/admin/logs')
@login_required
@admin_required
def admin_logs():
    """View all system logs."""
    logs = LogBook.query.order_by(LogBook.timestamp.desc()).all()
    return render_template('admin/logs.html', logs=logs)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page to change password."""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_user.check_password(current_password):
            flash('Current password is incorrect', 'danger')
        elif new_password != confirm_password:
            flash('New passwords do not match', 'danger')
        elif len(new_password) < 6:
            flash('Password must be at least 6 characters', 'danger')
        else:
            current_user.set_password(new_password)
            db.session.commit()
            log_action('password_change', 'Changed password')
            flash('Password updated successfully', 'success')
        return redirect(url_for('profile'))
    
    # Get user stats
    file_count = File.query.filter_by(user_id=current_user.id).count()
    total_size = db.session.query(db.func.sum(File.file_size)).filter_by(user_id=current_user.id).scalar() or 0
    
    return render_template('profile.html', file_count=file_count, total_size=total_size)


with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@example.com', role='admin')
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created")

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
