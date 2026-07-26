import { useEffect, useState } from 'react';
import { StickyNote, Trash2, Plus } from 'lucide-react';
import { SingleLayout } from '../components/layout/AppShell';
import { Card, CardHeader, CardBody } from '../components/ui/Card';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import EmptyState from '../components/ui/EmptyState';
import { useToast } from '../hooks/useToast';
import { dateTime } from '../lib/format';
import styles from './NotesPage.module.css';

const STORAGE_KEY = 'quantnest_notes';

const TAGS = ['general', 'bug', 'idea', 'todo', 'trade', 'review'];

const TAG_TONES = {
  general: 'neutral',
  bug: 'loss',
  idea: 'profit',
  todo: 'warning',
  trade: 'info',
  review: 'warning',
};

function readNotes() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export default function NotesPage() {
  const [notes, setNotes] = useState(readNotes);
  const [draft, setDraft] = useState('');
  const [tag, setTag] = useState('general');
  const [filter, setFilter] = useState('all');
  const toast = useToast();

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(notes));
    } catch {
      toast.error('Could not save notes', 'Local storage is unavailable in this browser.');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [notes]);

  const save = () => {
    const text = draft.trim();
    if (!text) return;

    setNotes((current) => [
      { id: crypto.randomUUID(), text, tag, timestamp: new Date().toISOString() },
      ...current,
    ]);
    setDraft('');
  };

  const remove = (id) => {
    setNotes((current) => current.filter((note) => note.id !== id));
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      save();
    }
  };

  const visible = filter === 'all' ? notes : notes.filter((note) => note.tag === filter);

  return (
    <SingleLayout>
      <Card>
        <CardHeader title="New note" subtitle="Saved locally in your browser" />
        <CardBody>
          <div className={styles.composer}>
            <div className={styles.tagRow}>
              {TAGS.map((option) => (
                <button
                  key={option}
                  type="button"
                  className={[styles.tagButton, tag === option ? styles.tagActive : '']
                    .filter(Boolean)
                    .join(' ')}
                  onClick={() => setTag(option)}
                >
                  {option}
                </button>
              ))}
            </div>

            <textarea
              className={styles.textarea}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Write a note about a trade, an idea or a bug…"
              aria-label="Note text"
            />

            <div className={styles.composerFooter}>
              <span className={styles.hint}>Press ⌘/Ctrl + Enter to save</span>
              <span className={styles.spacer} />
              <Button
                variant="primary"
                size="sm"
                onClick={save}
                disabled={!draft.trim()}
                leftIcon={<Plus size={14} strokeWidth={2} />}
              >
                Save note
              </Button>
            </div>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Notes"
          subtitle={`${notes.length} entr${notes.length === 1 ? 'y' : 'ies'}`}
          actions={
            <div className={styles.filterBar}>
              {['all', ...TAGS].map((option) => (
                <button
                  key={option}
                  type="button"
                  className={[styles.tagButton, filter === option ? styles.tagActive : '']
                    .filter(Boolean)
                    .join(' ')}
                  onClick={() => setFilter(option)}
                >
                  {option}
                </button>
              ))}
            </div>
          }
        />
        <CardBody>
          {visible.length === 0 ? (
            <EmptyState
              icon={<StickyNote size={20} strokeWidth={1.8} />}
              title={notes.length === 0 ? 'No notes yet' : 'No notes with this tag'}
              description={
                notes.length === 0
                  ? 'Use the composer above to capture your first note.'
                  : 'Try a different filter to see your other notes.'
              }
            />
          ) : (
            <div className={styles.noteList}>
              {visible.map((note) => (
                <article className={styles.note} key={note.id}>
                  <div className={styles.noteHead}>
                    <Badge tone={TAG_TONES[note.tag] ?? 'neutral'}>{note.tag}</Badge>
                    <span className={styles.noteTime}>{dateTime(note.timestamp ?? note.ts)}</span>
                    <div className={styles.noteActions}>
                      <Button
                        variant="ghost"
                        size="sm"
                        iconOnly
                        onClick={() => remove(note.id)}
                        aria-label="Delete note"
                      >
                        <Trash2 size={14} strokeWidth={2} />
                      </Button>
                    </div>
                  </div>
                  <p className={styles.noteBody}>{note.text}</p>
                </article>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </SingleLayout>
  );
}
