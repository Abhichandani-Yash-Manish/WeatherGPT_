import { NAV_GROUPS, NAV_NOTES, groupOf } from './navigation';
import { VIEWS } from './views';

describe('the top navigation', () => {
  it('places every registered surface in exactly one group, so no surface can drop out of the navigation', () => {
    const placed = NAV_GROUPS.flatMap(group => group.views);
    expect(new Set(placed).size).toBe(placed.length);
    expect(placed.slice().sort()).toEqual(VIEWS.map(view => view.id).sort());
    VIEWS.forEach(view => {
      expect(groupOf(view.id), view.id).toBeDefined();
      expect(NAV_NOTES[view.id], view.id).toBeTruthy();
    });
  });

  it('keeps the dashboard on the existing workspace route', () => {
    expect(groupOf('workspace')?.label).toBe('Dashboard');
    expect(VIEWS.find(view => view.id === 'workspace')?.label).toBe('Dashboard');
  });
});
