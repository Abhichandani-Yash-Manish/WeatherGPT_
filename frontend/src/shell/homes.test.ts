/* Every surface has exactly one home.

   The failure this prevents is a surface that exists, is routed, is tested, and is reachable from nothing —
   which this repository has had before: seven built API routes called by no UI, and four components
   imported by nobody. A view that no home lists is a view no reader can find. */

import { HOMES, homeOf, unplacedViews, viewsOf } from './homes';
import { VIEWS } from './views';

describe('the four homes', () => {
  it('places every registered view', () => {
    expect(unplacedViews(), 'these surfaces are in the registry but in no home').toEqual([]);
  });

  it('places each view only once', () => {
    const listed = HOMES.flatMap(home => home.views);
    const twice = listed.filter((id, index) => listed.indexOf(id) !== index);
    expect(twice, 'these surfaces are listed by more than one home').toEqual([]);
  });

  it('lists no view that the registry does not carry', () => {
    const known = new Set<string>(VIEWS.map(view => String(view.id)));
    const unknown = HOMES.flatMap(home => home.views).filter(id => !known.has(id));
    expect(unknown, 'these homes list a surface that does not exist').toEqual([]);
  });

  it('resolves each home to real registry entries, landing surface first', () => {
    HOMES.forEach(home => {
      const views = viewsOf(home);
      expect(views.length, home.id).toBe(home.views.length);
      expect(views[0].id, home.id + ' landing').toBe(home.views[0]);
    });
  });

  it('answers which home a surface belongs to', () => {
    expect(homeOf('warnings')?.id).toBe('warnings');
    expect(homeOf('climate')?.id).toBe('history');
    expect(homeOf('assistant')?.id).toBe('ask');
    expect(homeOf('nothing-like-this')).toBeUndefined();
  });
});
