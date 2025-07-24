from fastapi import FastAPI, Depends, HTTPException, status, Query, Path, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional

from .models import Base, User, Note
from .database import engine, get_db
from .schemas import (
    UserCreate, UserOut,
    Token,
    NoteCreate, NoteUpdate, NoteOut,
    Message,
)
from .auth import (
    authenticate_user, get_password_hash, create_access_token,
    get_current_active_user,
)

app = FastAPI(
    title="NoteMaster Backend",
    description="API for a fullstack notes app - user authentication and notes management.",
    version="0.1.0",
    openapi_tags=[
        {"name": "auth", "description": "User authentication & registration"},
        {"name": "notes", "description": "Notes CRUD, search, sort, filter"},
        {"name": "health", "description": "Health check endpoint"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# PUBLIC_INTERFACE
@app.on_event("startup")
def on_startup():
    """Create database tables if they do not exist (dev only). For production, use Alembic migrations."""
    Base.metadata.create_all(bind=engine)

# PUBLIC_INTERFACE
@app.get("/", tags=["health"], summary="Health Check", description="API health check endpoint.")
def health_check():
    """Health check endpoint."""
    return {"message": "Healthy"}


# -----------
# AUTH ROUTES
# -----------

# PUBLIC_INTERFACE
@app.post("/auth/register", response_model=UserOut, status_code=201, tags=["auth"],
          summary="Register new user",
          description="Register a new user (username, email, password required).")
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    if db.query(User).filter((User.username == user_in.username) | (User.email == user_in.email)).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email is already registered"
        )
    user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# PUBLIC_INTERFACE
@app.post("/auth/token", response_model=Token, tags=["auth"],
          summary="Login & obtain token",
          description="Obtain JWT access token via username & password (OAuth2 password flow).")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Get JWT token for login using username & password."""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

# (Logout is frontend/client-driven with JWTs—handled by deleting/invalidating token client-side)


# -----------
# USER ROUTES
# -----------

# PUBLIC_INTERFACE
@app.get("/users/me", response_model=UserOut, tags=["auth"],
         summary="Get current user profile",
         description="Get the current logged-in user's profile by JWT token.")
def read_users_me(
    current_user: User = Depends(get_current_active_user)
):
    """Returns current user's profile."""
    return current_user


# -----------
# NOTES ROUTES
# -----------

# PUBLIC_INTERFACE
@app.post("/notes/", response_model=NoteOut, status_code=201, tags=["notes"],
          summary="Create note",
          description="Create a new note belonging to the current user.")
def create_note(
    note_in: NoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a note for the current user."""
    note = Note(
        title=note_in.title,
        content=note_in.content,
        owner_id=current_user.id,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note

# PUBLIC_INTERFACE
@app.get("/notes/", response_model=List[NoteOut], tags=["notes"],
         summary="List/search notes",
         description="""Return all notes for current user, with filtering/sorting options.
- `q`: search by title substring
- `sort`: 'created', '-created', 'title', '-title'
- `limit`: Limit results (default 20)
""")
def list_notes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    q: Optional[str] = Query(None, description="Search query for titles"),
    sort: Optional[str] = Query("created", description="Sort by (created/title, prefix with '-' for descending)"),
    limit: int = Query(20, gt=0, le=100)
):
    """List/filter/sort notes for the user."""
    query = db.query(Note).filter(Note.owner_id == current_user.id)
    if q:
        query = query.filter(Note.title.ilike(f"%{q}%"))
    if sort:
        if sort.lstrip('-') not in ('created', 'title'):
            raise HTTPException(400, detail="Invalid sort key")
        direction = -1 if sort.startswith('-') else 1
        if sort.lstrip('-') == 'created':
            order = Note.created_at.desc() if direction == -1 else Note.created_at
        else:
            order = Note.title.desc() if direction == -1 else Note.title
        query = query.order_by(order)
    else:
        query = query.order_by(Note.created_at.desc())
    notes = query.limit(limit).all()
    return notes

# PUBLIC_INTERFACE
@app.get("/notes/{note_id}", response_model=NoteOut, tags=["notes"],
         summary="Get a note",
         description="Return a single note owned by current user.")
def get_note(
    note_id: int = Path(..., title="The ID of the note"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a note by ID if owned by current user."""
    note = db.query(Note).filter(Note.id == note_id, Note.owner_id == current_user.id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note

# PUBLIC_INTERFACE
@app.put("/notes/{note_id}", response_model=NoteOut, tags=["notes"],
         summary="Update note",
         description="Update an existing note (owner only).")
def update_note(
    note_id: int,
    note_in: NoteUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update note fields if owned by current user."""
    note = db.query(Note).filter(Note.id == note_id, Note.owner_id == current_user.id).first()
    if not note:
        raise HTTPException(404, detail="Note not found")
    if note_in.title is not None:
        note.title = note_in.title
    if note_in.content is not None:
        note.content = note_in.content
    db.commit()
    db.refresh(note)
    return note

# PUBLIC_INTERFACE
@app.delete("/notes/{note_id}", response_model=Message, tags=["notes"],
            summary="Delete note",
            description="Delete a note by ID (owner only).")
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a note by ID if owned by current user."""
    note = db.query(Note).filter(Note.id == note_id, Note.owner_id == current_user.id).first()
    if not note:
        raise HTTPException(404, detail="Note not found")
    db.delete(note)
    db.commit()
    return {"detail": "Note deleted."}

