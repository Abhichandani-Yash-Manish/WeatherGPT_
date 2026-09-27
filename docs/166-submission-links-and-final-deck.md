# Submission links and final deck

27 September 2026. Documentation and submission packaging only; no product code or acceptance status changed.

- [Published demonstration](https://youtu.be/NVT6EnklEVQ) — 7:15, Team Void Pointers, team 118709, SIH26068.
- [Submission PDF](../WeatherGPT_SIH26068_VoidPointers_FINAL.pdf).
- [Editable PowerPoint](../WeatherGPT_SIH26068_VoidPointers_FINAL.pptx).

The current presentation is a link-only update of the user's original PowerPoint and approved PDF. Both QR codes encode the published video and are clickable, as are their visible “Scan or click” labels. The original source-code line remains. The README places the video beside the deck and provides timestamped shortcuts to the demonstrated journeys.

The earlier packaging revision in commit `87089c4` also revised slide copy and used an exporter that replaced document metadata and speaker notes. The user requested preservation of the original presentation's internal tuning, so that revision is superseded. This correction restores the original content and package structure, with only the demo links, QR artwork and two labels changed. It does not re-evaluate or extend product acceptance; the README's current scope table and [full product account](140-the-full-account.md) retain those distinctions.

## Packaging checks

- All 128 original PPTX package parts remain. Only five parts differ: the two relevant slide XML files, their hyperlink relationships, and their shared QR image. The other 123 parts are byte-identical, including document properties, notes, masters and themes. Unrelated objects within the two changed slides are also unchanged.
- The PDF was patched directly from the approved original, preserving its metadata and existing document structure. Extracted text differs only in the two QR labels. Rendered pixels outside the QR and label areas are identical on all six pages.
- Both rendered QR codes decode to the final video URL. PDF annotations and PowerPoint hyperlink relationships point to the same destination. Label click targets stay clear of the original source-code line.
- PowerPoint package, six-slide geometry and re-import checks pass. The rendered PowerPoint labels and their links were checked as well.
- These are preservation and packaging checks, not a rerun of the user's original ATS tests or a claim of an ATS score.
- The new YouTube page opens while signed out and sampled playback was verified. Browser playback encountered intermittent player errors, so this does not claim uninterrupted playback on every device.
- README relative links resolve; its original architecture diagrams and map are preserved.

The video combines recorded product screens, implementation evidence and a labelled prepared farmer summary. Its mobile segment demonstrates responsive browser layout, not real-device acceptance. No runtime databases, private conversations, voice recordings or video-production intermediates are included in this publication.
