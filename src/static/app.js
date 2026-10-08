class NoteTaker {
  constructor() {
    this.notes = [];
    this.folders = [];
    this.currentNote = null;
    this.selectedFolderId = 'all';
    this.isLoading = false;
    this.pendingFolderAction = null;
    this.init();
  }

  async init() {
    this.bindEvents();
    await Promise.all([this.loadFolders(), this.loadNotes()]);
  }

  bindEvents() {
    document.getElementById('newNoteBtn').addEventListener('click', () => this.createNewNote());
    const folderButton = document.getElementById('newFolderBtn');
    if (folderButton) {
      folderButton.addEventListener('click', () => this.createFolder());
    }
    document.getElementById('folderBackBtn').addEventListener('click', () => {
      this.selectedFolderId = 'all';
      this.renderFolderList();
      this.renderNotesList();
    });
    document.getElementById('folderForm').addEventListener('submit', (event) => {
      event.preventDefault();
      const value = document.getElementById('folderNameInput').value.trim();
      if (typeof this.pendingFolderAction === 'function') {
        this.pendingFolderAction(value);
      }
    });
    document.getElementById('folderCancelBtn').addEventListener('click', () => this.closeFolderModal());
    document.getElementById('saveBtn').addEventListener('click', () => this.saveNote());
    document.getElementById('deleteBtn').addEventListener('click', () => this.deleteNote());
    document.getElementById('translateBtn').addEventListener('click', () => this.toggleTranslateToolbar());
    document.getElementById('translateToolbar').addEventListener('click', (event) => {
      const languageButton = event.target.closest('[data-target-language]');
      if (languageButton) {
        this.translateNote(languageButton.dataset.targetLanguage);
      }
    });
    document.addEventListener('click', (event) => {
      if (!event.target.closest('.translate-control')) {
        this.toggleTranslateToolbar(false);
      }
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        this.toggleTranslateToolbar(false);
      }
    });
    document.getElementById('searchBox').addEventListener('input', (e) => this.searchNotes(e.target.value));
    document.getElementById('foldersList').addEventListener('click', (event) => {
      const actionTarget = event.target.closest('[data-folder-action]');
      if (actionTarget) {
        const folderId = Number(actionTarget.dataset.folderId);
        const action = actionTarget.dataset.folderAction;

        if (action === 'rename') {
          this.renameFolder(folderId);
        } else if (action === 'delete') {
          this.deleteFolder(folderId);
        }
        return;
      }

      const folderButton = event.target.closest('[data-folder-id]');
      if (folderButton) {
        this.selectedFolderId = folderButton.dataset.folderId;
        this.renderFolderList();
        this.renderNotesList();
      }
    });

  }

  async loadFolders() {
    try {
      const response = await fetch('/api/folders');
      if (!response.ok) throw new Error('Failed to load folders');
      this.folders = await response.json();
      this.renderFolderList();
      this.populateFolderSelect();
    } catch (error) {
      this.showMessage(`Error loading folders: ${error.message}`, 'error');
    }
  }

  async loadNotes() {
    this.isLoading = true;
    this.showMessage('Loading notes...', 'loading');

    try {
      const response = await fetch('/api/notes');
      if (!response.ok) throw new Error('Failed to load notes');

      this.notes = await response.json();
      this.renderFolderList();
      this.renderNotesList();
      this.hideMessage();
    } catch (error) {
      this.showMessage(`Error loading notes: ${error.message}`, 'error');
    } finally {
      this.isLoading = false;
    }
  }

  renderFolderList() {
    const foldersList = document.getElementById('foldersList');
    const folderPanel = document.querySelector('.folder-panel');
    const folderBackButton = document.getElementById('folderBackBtn');
    const folderViewTitle = document.getElementById('folderViewTitle');
    const newFolderButton = document.getElementById('newFolderBtn');
    const selectedFolder = this.selectedFolderId === 'all'
      ? null
      : this.folders.find(folder => String(folder.id) === String(this.selectedFolderId));
    const isInFolder = Boolean(selectedFolder);

    folderPanel.hidden = false;
    folderBackButton.hidden = !isInFolder;
    folderViewTitle.textContent = selectedFolder ? selectedFolder.name : 'Folders';
    newFolderButton.hidden = isInFolder;
    foldersList.hidden = isInFolder;

    const allFolder = `
      <div class="folder-row">
        <button type="button" class="folder-item ${this.selectedFolderId === 'all' ? 'active' : ''}" data-folder-id="all">
          <span>All notes</span>
          <small>${this.notes.length}</small>
        </button>
      </div>
    `;

    const folderMarkup = this.folders.map(folder => `
      <div class="folder-row">
        <button type="button" class="folder-item ${String(this.selectedFolderId) === String(folder.id) ? 'active' : ''}" data-folder-id="${folder.id}">
          <span>${window.NoteTakerUtils.escapeHtml(folder.name)}</span>
          <small>${folder.note_count || 0}</small>
        </button>
        <div class="folder-actions">
          <button type="button" data-folder-action="rename" data-folder-id="${folder.id}" title="Rename folder">✏️</button>
          <button type="button" data-folder-action="delete" data-folder-id="${folder.id}" title="Delete folder">🗑️</button>
        </div>
      </div>
    `).join('');

    foldersList.innerHTML = allFolder + folderMarkup;
  }

  populateFolderSelect() {
    const folderSelect = document.getElementById('noteFolder');
    const currentValue = this.currentNote && this.currentNote.folder_id ? String(this.currentNote.folder_id) : '';
    folderSelect.innerHTML = '<option value="">Unfiled</option>' + this.folders.map(folder => `
      <option value="${folder.id}">${window.NoteTakerUtils.escapeHtml(folder.name)}</option>
    `).join('');
    folderSelect.value = currentValue;
  }

  getVisibleNotes() {
    const query = document.getElementById('searchBox').value.trim().toLowerCase();
    const allNotes = this.selectedFolderId === 'all'
      ? this.notes
      : this.notes.filter(note => Number(note.folder_id) === Number(this.selectedFolderId));

    if (!query) {
      return allNotes;
    }

    return allNotes.filter(note =>
      (note.title && note.title.toLowerCase().includes(query)) ||
      (note.content && note.content.toLowerCase().includes(query))
    );
  }

  renderNotesList() {
    const notesList = document.getElementById('notesList');
    const visibleNotes = this.getVisibleNotes();

    if (visibleNotes.length === 0) {
      notesList.innerHTML = '<div class="empty-state"><p>No notes in this view yet.</p></div>';
      return;
    }

    notesList.innerHTML = visibleNotes.map(note => `
      <div class="note-item ${this.currentNote && this.currentNote.id === note.id ? 'active' : ''}" 
           data-note-id="${note.id}" onclick="noteTaker.selectNote(${note.id})">
        <div class="note-title">${window.NoteTakerUtils.escapeHtml(note.title || 'Untitled')}</div>
        <div class="note-preview">${window.NoteTakerUtils.escapeHtml(note.content || 'No content')}</div>
        <div class="note-date">${window.NoteTakerUtils.formatDate(note.updated_at)}</div>
      </div>
    `).join('');
  }

  async selectNote(noteId) {
    const note = this.notes.find(n => n.id === noteId);
    if (!note) return;

    this.currentNote = note;
    this.showEditor();
    this.renderNotesList();
    this.populateFolderSelect();

    document.getElementById('noteTitle').value = note.title || '';
    document.getElementById('noteContent').value = note.content || '';
    document.getElementById('editorTitle').textContent = note.title || 'Untitled Note';
    const folderSelect = document.getElementById('noteFolder');
    folderSelect.value = note.folder_id ? String(note.folder_id) : '';
  }

  createNewNote() {
    this.currentNote = {
      id: null,
      title: '',
      content: '',
      folder_id: this.selectedFolderId !== 'all' ? Number(this.selectedFolderId) : null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };

    this.showEditor();
    document.getElementById('noteTitle').value = '';
    document.getElementById('noteContent').value = '';
    document.getElementById('editorTitle').textContent = 'New Note';
    this.populateFolderSelect();
    const folderSelect = document.getElementById('noteFolder');
    folderSelect.value = this.currentNote.folder_id ? String(this.currentNote.folder_id) : '';
    document.getElementById('noteTitle').focus();

    document.querySelectorAll('.note-item').forEach(item => {
      item.classList.remove('active');
    });
  }

  showEditor() {
    document.getElementById('emptyState').style.display = 'none';
    document.getElementById('editorForm').style.display = 'flex';
    document.getElementById('editorActions').style.display = 'flex';
    document.getElementById('deleteBtn').hidden = !this.currentNote || !this.currentNote.id;
  }

  hideEditor() {
    this.toggleTranslateToolbar(false);
    document.getElementById('emptyState').style.display = 'block';
    document.getElementById('editorForm').style.display = 'none';
    document.getElementById('editorActions').style.display = 'none';
    document.getElementById('editorTitle').textContent = 'Select a note to edit';
    this.currentNote = null;
  }

  toggleTranslateToolbar(forceOpen) {
    const toolbar = document.getElementById('translateToolbar');
    const button = document.getElementById('translateBtn');
    const isOpen = forceOpen === undefined ? toolbar.classList.contains('hidden') : forceOpen;
    toolbar.classList.toggle('hidden', !isOpen);
    button.setAttribute('aria-expanded', String(isOpen));
  }

  async translateNote(targetLanguage) {
    const note = this.currentNote;
    const content = document.getElementById('noteContent').value.trim();
    if (!note) return;
    if (!content) {
      this.showMessage('Enter note content before translating.', 'error');
      return;
    }

    this.toggleTranslateToolbar(false);
    const translateButton = document.getElementById('translateBtn');
    translateButton.disabled = true;
    this.showMessage(`Translating to ${targetLanguage}...`, 'loading');

    try {
      const response = await fetch('/api/notes/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, target_language: targetLanguage })
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Translation failed');
      if (this.currentNote !== note) return;

      document.getElementById('noteContent').value = result.translation;
      this.showMessage(`Translated to ${targetLanguage}. Click Save to keep this change.`, 'success');
    } catch (error) {
      this.showMessage(`Translation failed: ${error.message}`, 'error');
    } finally {
      translateButton.disabled = false;
    }
  }

  async saveNote() {
    if (!this.currentNote) return;

    const title = document.getElementById('noteTitle').value.trim();
    const content = document.getElementById('noteContent').value.trim();
    const folderId = document.getElementById('noteFolder').value;

    if (!title && !content) {
      this.showMessage('Please enter a title or content', 'error');
      return;
    }

    try {
      const noteData = {
        title: title || 'Untitled',
        content: content,
        folder_id: folderId === '' ? null : Number(folderId)
      };

      let response;
      if (this.currentNote.id) {
        response = await fetch(`/api/notes/${this.currentNote.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(noteData)
        });
      } else {
        response = await fetch('/api/notes', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(noteData)
        });
      }

      if (!response.ok) throw new Error('Failed to save note');

      const savedNote = await response.json();
      this.currentNote = savedNote;
      document.getElementById('deleteBtn').hidden = false;

      const existingIndex = this.notes.findIndex(n => n.id === savedNote.id);
      if (existingIndex >= 0) {
        this.notes[existingIndex] = savedNote;
      } else {
        this.notes.unshift(savedNote);
      }

      await this.loadFolders();
      this.renderFolderList();
      this.renderNotesList();
      this.populateFolderSelect();
      document.getElementById('editorTitle').textContent = savedNote.title;

      this.showMessage('Note saved successfully!', 'success');
    } catch (error) {
      this.showMessage(`Error saving note: ${error.message}`, 'error');
    }
  }

  async deleteNote() {
    if (!this.currentNote || !this.currentNote.id) return;

    if (!confirm('Are you sure you want to delete this note?')) return;

    try {
      const response = await fetch(`/api/notes/${this.currentNote.id}`, {
        method: 'DELETE'
      });

      if (!response.ok) throw new Error('Failed to delete note');

      this.notes = this.notes.filter(n => n.id !== this.currentNote.id);
      await this.loadFolders();
      this.renderFolderList();
      this.renderNotesList();
      this.hideEditor();
      this.showMessage('Note deleted successfully!', 'success');
    } catch (error) {
      this.showMessage(`Error deleting note: ${error.message}`, 'error');
    }
  }

  openFolderModal(title, currentValue, onSubmit) {
    const modal = document.getElementById('folderModal');
    const titleElement = document.getElementById('folderModalTitle');
    const input = document.getElementById('folderNameInput');

    titleElement.textContent = title;
    input.value = currentValue || '';
    input.focus();
    input.select();
    this.pendingFolderAction = (value) => {
      this.closeFolderModal();
      onSubmit(value);
    };
    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');
  }

  closeFolderModal() {
    const modal = document.getElementById('folderModal');
    modal.classList.add('hidden');
    modal.setAttribute('aria-hidden', 'true');
    document.getElementById('folderNameInput').value = '';
    this.pendingFolderAction = null;
  }

  async createFolder() {
    this.openFolderModal('Create folder', '', async (name) => {
      if (!name || !name.trim()) return;

      try {
        const response = await fetch('/api/folders', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: name.trim() })
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.error || 'Failed to create folder');
        }

        const folder = await response.json();
        this.selectedFolderId = String(folder.id);
        await this.loadFolders();
        this.loadNotes();
        this.showMessage(`Folder "${folder.name}" created.`, 'success');
      } catch (error) {
        this.showMessage(`Error creating folder: ${error.message}`, 'error');
      }
    });
  }

  async renameFolder(folderId) {
    const folder = this.folders.find(item => item.id === folderId);
    if (!folder) return;

    this.openFolderModal('Rename folder', folder.name, async (newName) => {
      if (!newName || !newName.trim()) return;

      try {
        const response = await fetch(`/api/folders/${folderId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: newName.trim() })
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.error || 'Failed to rename folder');
        }

        await this.loadFolders();
        this.renderNotesList();
        this.showMessage('Folder renamed successfully!', 'success');
      } catch (error) {
        this.showMessage(`Error renaming folder: ${error.message}`, 'error');
      }
    });
  }

  async deleteFolder(folderId) {
    const folder = this.folders.find(item => item.id === folderId);
    if (!folder) return;

    if (!confirm(`Delete folder "${folder.name}"? Its notes will remain unfiled.`)) return;

    try {
      const response = await fetch(`/api/folders/${folderId}`, {
        method: 'DELETE'
      });

      if (!response.ok) throw new Error('Failed to delete folder');

      this.selectedFolderId = 'all';
      await this.loadFolders();
      await this.loadNotes();
      this.showMessage('Folder deleted successfully!', 'success');
    } catch (error) {
      this.showMessage(`Error deleting folder: ${error.message}`, 'error');
    }
  }

  searchNotes(query) {
    const notesList = document.getElementById('notesList');
    const filteredNotes = this.getVisibleNotes();

    if (filteredNotes.length === 0) {
      notesList.innerHTML = '<div class="empty-state"><p>No notes found matching your search.</p></div>';
      return;
    }

    notesList.innerHTML = filteredNotes.map(note => `
      <div class="note-item ${this.currentNote && this.currentNote.id === note.id ? 'active' : ''}" 
           data-note-id="${note.id}" onclick="noteTaker.selectNote(${note.id})">
        <div class="note-title">${window.NoteTakerUtils.escapeHtml(note.title || 'Untitled')}</div>
        <div class="note-preview">${window.NoteTakerUtils.escapeHtml(note.content || 'No content')}</div>
        <div class="note-date">${window.NoteTakerUtils.formatDate(note.updated_at)}</div>
      </div>
    `).join('');
  }

  showMessage(message, type) {
    const messageArea = document.getElementById('messageArea');
    messageArea.innerHTML = `<div class="${type}">${message}</div>`;

    if (type === 'success') {
      setTimeout(() => this.hideMessage(), 3000);
    }
  }

  hideMessage() {
    document.getElementById('messageArea').innerHTML = '';
  }
}

window.noteTaker = new NoteTaker();
