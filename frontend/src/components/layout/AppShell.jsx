import styles from './AppShell.module.css';

export function AppShell({ topBar, children }) {
  return (
    <div className={styles.shell}>
      {topBar}
      <main className={styles.main}>{children}</main>
    </div>
  );
}

/** Workspace layout: fixed order-ticket rail + scrollable dashboard. */
export function SplitLayout({ side, children }) {
  return (
    <div className={styles.split}>
      <aside className={styles.sidePanel}>{side}</aside>
      <section className={styles.content}>
        <div className={styles.contentInner}>{children}</div>
      </section>
    </div>
  );
}

/** Single-column layout for content pages. */
export function SingleLayout({ children }) {
  return (
    <section className={styles.single}>
      <div className={styles.singleInner}>{children}</div>
    </section>
  );
}

export default AppShell;
