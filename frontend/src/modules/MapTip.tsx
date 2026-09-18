/* The hover tip both maps share. It follows the pointer (fixed positioning, viewport coordinates) and
   states what the feature's own row said, in the same words the readout line uses. Nothing here is a value
   the read did not return: an absent colour is the words 'colour not stated'. */
import { ColourTag } from './Evidence';

export type TipState = {
  x: number; y: number;
  name: string;
  state?: string | null;
  colour?: string | null;
  colourText?: string;
  wording?: string;
  meta?: string;
  clock?: string;
} | null;

export function MapTip({ tip }: { tip: TipState }): JSX.Element | null {
  if (!tip) return null;
  return (
    <div className="map-tip" role="tooltip" data-testid="map-tip" style={{ left: tip.x + 16, top: tip.y + 16 }}>
      <p className="map-tip-name m-0">{tip.name}{tip.state ? ' · ' + tip.state : ''}</p>
      <p className="map-tip-line m-0">
        <ColourTag colour={tip.colour} text={tip.colourText || tip.colour || 'colour not stated'} />
        {tip.wording ? <span>{tip.wording}</span> : null}
      </p>
      {tip.meta ? <p className="map-tip-line map-tip-code m-0">{tip.meta}</p> : null}
      {tip.clock ? <p className="map-tip-line map-tip-code m-0">{tip.clock}</p> : null}
    </div>
  );
}
