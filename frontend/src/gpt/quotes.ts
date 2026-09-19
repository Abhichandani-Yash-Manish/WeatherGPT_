/* A line for the hour.
   ============================================================================
   One short line of verse under the reading, changed by the hour the ground is in and the month the reader
   is in, drawn from a small curated corpus.

   Two rules hold this file together, and both come from the same place as the rest of the product:

   1. Every line is VERIFIED. Each was checked against a named edition before it was written here — the two
      Tagore collections and Blake and Dickinson from Project Gutenberg, Rossetti from the Academy of
      American Poets, Shelley from his collected poems — and the basis travels with the line so the wording
      can be checked again rather than trusted. A quotation quoted from memory is an invented value.

   2. Every line is PUBLIC DOMAIN in the editions named. Nothing here is under copyright, nothing is
      paraphrased, and nothing is machine-translated: a line in a language the product cannot write honestly
      would be exactly the kind of claim docs/30 exists to refuse. The corpus is English, which is the
      language this screen already speaks, and offering it per-reader-language is a recorded open item.

   The line is chosen deterministically — the same reader at the same hour on the same day sees the same
   line, and it turns four times a day. Nothing here is a weather statement: a line about rain is printed on
   a clear afternoon too, which is why most lines are tagged to a time of day or a season rather than to what
   the sky is doing. The one thing this file must never do is imply that the verse was written about today. */

import type { Hour } from './fieldPaint';

export type Quote = {
  id: string;
  /** The line as the edition printed it, in the edition's own punctuation. */
  text: string;
  author: string;
  work: string;
  year: number;
  /** The edition the wording was checked against, kept so the check can be repeated. */
  basis: string;
  /** The hours the line reads true in. Absent means any hour. */
  hours?: Hour[];
  /** The months the line belongs to, 1–12. Absent means any month. */
  months?: number[];
};

export const QUOTES: Quote[] = [
  {
    id: 'tagore-watercups',
    text: 'The clouds fill the watercups of the river, hiding themselves in the distant hills.',
    author: 'Rabindranath Tagore', work: 'Stray Birds', year: 1916,
    basis: 'Project Gutenberg #6524, Stray Birds, verse 174',
    hours: ['noon'], months: [6, 7, 8, 9],
  },
  {
    id: 'tagore-humbly',
    text: 'The cloud stood humbly in a corner of the sky. The morning crowned it with splendour.',
    author: 'Rabindranath Tagore', work: 'Stray Birds', year: 1916,
    basis: 'Project Gutenberg #6524, Stray Birds, verse 100',
    hours: ['daybreak'],
  },
  {
    id: 'tagore-western-sea',
    text: 'The sun goes to cross the Western sea, leaving its last salutation to the East.',
    author: 'Rabindranath Tagore', work: 'Stray Birds', year: 1916,
    basis: 'Project Gutenberg #6524, Stray Birds, verse 39',
    hours: ['golden'],
  },
  {
    id: 'tagore-sunset-cloud',
    text: '“My heart is like the golden casket of thy kiss,” said the sunset cloud to the sun.',
    author: 'Rabindranath Tagore', work: 'Stray Birds', year: 1916,
    basis: 'Project Gutenberg #6524, Stray Birds, verse 196',
    hours: ['golden'],
  },
  {
    id: 'tagore-fireflies',
    text: 'The stars are not afraid to appear like fireflies.',
    author: 'Rabindranath Tagore', work: 'Stray Birds', year: 1916,
    basis: 'Project Gutenberg #6524, Stray Birds, verse 48',
    hours: ['night'],
  },
  {
    id: 'tagore-bird-cloud',
    text: 'The bird wishes it were a cloud. The cloud wishes it were a bird.',
    author: 'Rabindranath Tagore', work: 'Stray Birds', year: 1916,
    basis: 'Project Gutenberg #6524, Stray Birds, verse 35',
  },
  {
    id: 'tagore-rainy-july',
    text: 'In the deep shadows of the rainy July, with secret steps, thou walkest, silent as night, eluding all watchers.',
    author: 'Rabindranath Tagore', work: 'Gitanjali', year: 1912,
    basis: 'Academy of American Poets, Gitanjali 22',
    hours: ['night'], months: [7, 8],
  },
  {
    /* Kabir through Tagore's own English, which is the edition this wording was checked against. The couplet
       is about the first rain of the season, and it is tagged to the monsoon months because that is when it
       reads as what it is. */
    id: 'kabir-clouds-thicken',
    text: 'Clouds thicken in the sky! O, listen to the deep voice of their roaring; the rain comes from the east with its monotonous murmur.',
    author: 'Kabir', work: 'Songs of Kabir, translated by Rabindranath Tagore', year: 1915,
    basis: 'Project Gutenberg #6519, Songs of Kabir, poem I.71',
    months: [6, 7, 8, 9],
  },
  {
    id: 'kabir-sky-roars',
    text: 'The sky roars and the lightning flashes, the waves arise in my heart; the rain falls, and my heart longs for my Lord.',
    author: 'Kabir', work: 'Songs of Kabir, translated by Rabindranath Tagore', year: 1915,
    basis: 'Project Gutenberg #6519, Songs of Kabir, poem LXXXVIII',
    months: [6, 7, 8, 9],
  },
  {
    id: 'kalidasa-harbinger',
    text: '…the harbinger of rain, a cloud that charged the peak in mimic fray.',
    author: 'Kalidasa', work: 'The Cloud Messenger, translated by Arthur W. Ryder', year: 1912,
    basis: 'Project Gutenberg #16659, Translations of Shakuntala and Other Works, The Cloud-Messenger II',
    months: [6, 7, 8, 9],
  },
  {
    id: 'rossetti-wind',
    text: 'Who has seen the wind? Neither I nor you. But when the leaves hang trembling, the wind is passing through.',
    author: 'Christina Rossetti', work: 'Sing-Song: A Nursery Rhyme Book', year: 1872,
    basis: 'Academy of American Poets, Who Has Seen the Wind?',
  },
  {
    id: 'shelley-showers',
    text: 'I bring fresh showers for the thirsting flowers, from the seas and the streams.',
    author: 'Percy Bysshe Shelley', work: 'The Cloud', year: 1820,
    basis: 'Project Gutenberg #4800, The Complete Poetical Works of Percy Bysshe Shelley, The Cloud',
    hours: ['daybreak', 'noon'], months: [6, 7, 8, 9],
  },
  {
    id: 'dickinson-shower',
    text: 'A drop fell on the apple tree, another on the roof; a half a dozen kissed the eaves, and made the gables laugh.',
    author: 'Emily Dickinson', work: 'Summer Shower', year: 1890,
    basis: 'Project Gutenberg #12242, Poems by Emily Dickinson, Three Series, Complete',
    hours: ['noon'], months: [6, 7, 8, 9],
  },
  {
    id: 'blake-sun',
    text: 'The sun does arise, and make happy the skies.',
    author: 'William Blake', work: 'The Echoing Green, in Songs of Innocence', year: 1789,
    basis: 'Project Gutenberg #1934, Songs of Innocence and of Experience',
    hours: ['daybreak'],
  },
];

export function lineFor(at: Date, hour: Hour): Quote {
  return linesFor(at, hour)[0];
}

/** The lines that read true at this hour and month, nearest first: the hour's own, then the season's, then the
    lines that belong to any hour at all. */
export function linesFor(at: Date, hour: Hour): Quote[] {
  const month = at.getMonth() + 1;
  const fits = (quote: Quote) => !quote.months || quote.months.includes(month);
  const forHour = QUOTES.filter(quote => fits(quote) && quote.hours?.includes(hour));
  const forSeason = QUOTES.filter(quote => fits(quote) && !quote.hours && quote.months);
  const forAny = QUOTES.filter(quote => !quote.hours && !quote.months);
  const pool = forHour.length ? forHour : forSeason.length ? forSeason : forAny;
  /* Deterministic, and stable for an hour: the day number and the hour together choose the line, so it turns
     four times a day and no two readers see a different line in the same hour. */
  const day = Math.floor(at.getTime() / 86_400_000);
  const hourIndex = ['daybreak', 'noon', 'golden', 'night'].indexOf(hour);
  const offset = (day + hourIndex) % pool.length;
  return [...pool.slice(offset), ...pool.slice(0, offset)];
}

/** The next line, for a reader who asks for another one. Wraps around the pool the hour allows. */
export function nextLine(current: Quote, at: Date, hour: Hour): Quote {
  const pool = linesFor(at, hour);
  const index = pool.findIndex(quote => quote.id === current.id);
  return pool[(index + 1) % pool.length];
}
