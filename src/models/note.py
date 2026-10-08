from datetime import datetime

from src.models.user import db


class Note(db.Model):
    __tablename__ = 'note'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    folder_id = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=True)
    folder = db.relationship('Folder', backref=db.backref('notes', lazy='dynamic'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Note {self.title}>'

    def to_dict(self):
        folder = self.folder.name if self.folder else None
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'folder_id': self.folder_id,
            'folder_name': folder,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

