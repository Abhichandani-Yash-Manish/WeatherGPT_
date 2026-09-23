import { ChevronDown, Languages } from 'lucide-react';
import { ListBox, Select } from '@heroui/react';
import type { ComposerProps } from './Composer';

export default function LanguagePicker({ language, languages, onLanguage, languageState = 'ready' }: Pick<ComposerProps, 'language' | 'languages' | 'onLanguage' | 'languageState'>) {
  return (
          <Select
            className="g-composer-language"
            aria-label="Answer language"
            value={language || 'auto'}
            onChange={key => onLanguage?.(key === 'auto' ? '' : String(key))}
            isDisabled={languageState !== 'ready' || !onLanguage}
          >
            <Select.Trigger className="g-language-trigger">
              <Languages size={15} aria-hidden="true" />
              <span>{languageState === 'loading' ? 'Languages…' : languageState === 'error' ? 'Languages unavailable' : languages?.find(entry => entry.code === language)?.label || (language || 'Auto')}</span>
              <ChevronDown size={13} aria-hidden="true" />
            </Select.Trigger>
            <Select.Popover className="g-language-popover" placement="top start" style={{ maxHeight: 'min(380px, 60dvh)' }}>
              <p className="g-language-heading">Answer language</p>
              <p className="g-language-note">Applies to your next question.</p>
              <ListBox className="g-language-options" aria-label="Answer language">
                {[{ code: 'auto', label: 'Auto — match the question' }, ...(languages || [])].map(entry => (
                  <ListBox.Item key={entry.code} id={entry.code} textValue={entry.label} className="g-language-option">
                    <span>{entry.label}</span><ListBox.ItemIndicator />
                  </ListBox.Item>
                ))}
              </ListBox>
            </Select.Popover>
          </Select>
  );
}
