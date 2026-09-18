/* The aurora field: three drifting washes and a slow grid over the ground, behind every surface.
   Decoration, and it says so: it carries no value, no state and no colour a reading uses. The sky band
   (shell/SkyBackground.tsx) still sets the time-of-day tint on top of it, and a surface paints its own
   glass panel over both. */
export function Aurora(): JSX.Element {
  return (
    <div className="aurora" aria-hidden="true" data-aurora="field">
      <span className="aurora-blob aurora-blob-a" />
      <span className="aurora-blob aurora-blob-b" />
      <span className="aurora-blob aurora-blob-c" />
      <span className="aurora-veil" />
    </div>
  );
}
