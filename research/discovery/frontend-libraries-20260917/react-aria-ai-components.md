# AI Components

React Spectrum provides components for building AI-powered experiences, including prompts, messages, suggestions, attachments, and voice input.

```tsx
import {useState, useRef} from 'react';
import {
  AttachFileMenuItem,
  CommandMenuItem,
  InsertTokenMenuItem,
  InsertMenuButton,
  PromptField,
  Attachment,
  AttachmentPreview,
  PromptFieldAttachment,
  PromptFieldAttachmentList,
  PromptFieldSubmitButton,
  PromptFieldToolbar,
  PromptFieldValue,
  PromptFieldVoiceButton,
  PromptToken,
  PromptTokenField
} from '@react-spectrum/ai';
import {type FocusableRefValue} from '@react-types/shared';
import {getIcon, slashCommands, objects, renderCompletions, suggestions, type UploadState} from './ai-component-helpers/promptfield';
import {style} from '@react-spectrum/s2/style' with {type: 'macro'};
import {Collection, SubmenuTrigger, Menu, MenuItem, MenuSection, Header, Heading, Text} from '@react-spectrum/s2';
import Data from '@react-spectrum/s2/icons/Data';
import Plugin from '@react-spectrum/s2/icons/Plugin';
import Prompt from '@react-spectrum/s2/icons/Prompt';
import {VirtualizedStreamingChat} from './ai-component-helpers/chat';

function Example() {
  let [value, setValue] = useState<PromptFieldValue>(() => new PromptFieldValue([]));
  let promptFieldRef = useRef<FocusableRefValue<HTMLDivElement>>(null);
  let [attachments, setAttachments] = useState<PromptFieldAttachment[]>([]);
  let [attachmentState, setAttachmentState] = useState<Map<string, UploadState>>(new Map());

  let mockUpload = async (id: string) => {
    await new Promise(resolve => setTimeout(resolve, Math.random() * 30));
    setAttachmentState(prev => {
      let item = prev.get(id);
      if (!item || item.status === 'completed') {
        return prev;
      }
      let newState = new Map(prev);
      let progress = (item.progress ?? 0) + 1;
      if (progress >= 100) {
        newState.set(id, {status: 'completed'});
      } else {
        newState.set(id, {status: 'uploading', progress});
        mockUpload(id);
      }
      return newState;
    });
  };

  let clearPrompt = () => {
    setValue(new PromptFieldValue([]));
    setAttachments([]);
    alert('Conversation cleared');
  };

  let compactPrompt = () => {
    alert('Conversation compacted');
  };

  return (
    <div className={style({height: 700, width: 'full'})}>
      {/*- begin focus -*/}
      <VirtualizedStreamingChat
        suggestions={suggestions}
        onSelectSuggestion={value => {
          setValue(value as PromptFieldValue);
          promptFieldRef.current?.focus();
        }}>
        {/*- end focus -*/}
        {(onSend, isGenerating) => (
          <PromptField
            ref={promptFieldRef}
            value={value}
            onChange={setValue}
            attachments={attachments}
            onAttachmentsChange={setAttachments}
            isGenerating={isGenerating}
            onSubmit={prompt => {
              onSend(prompt);
              setValue(new PromptFieldValue([]));
              setAttachments([]);
              setAttachmentState(new Map());
            }}
            acceptedAttachmentTypes={['*/*']}
            onAddAttachments={newAttachments => {
              setAttachmentState(prev => {
                let newState = new Map(prev);
                newAttachments.forEach(attachment => {
                  newState.set(attachment.id, {status: 'uploading', progress: 0});
                  mockUpload(attachment.id);
                });
                return newState;
              });
            }}
            onRemoveAttachments={removedAttachments => {
              setAttachmentState(prev => {
                let newState = new Map(prev);
                removedAttachments.forEach(attachment => {
                  newState.delete(attachment.id);
                });
                return newState;
              });
            }}>
            <PromptFieldAttachmentList dependencies={[attachmentState]}>
              {attachment => {
                let state = attachmentState.get(attachment.id);
                return (
                  <Attachment uploadProgress={state?.status === 'uploading' ? state?.progress : undefined}>
                    <AttachmentPreview mimeType={attachment.file.type} src={attachment.image} />
                  </Attachment>
                );
              }}
            </PromptFieldAttachmentList>
            <PromptTokenField
              completionTrigger={/(?<=^|\s)[@/]/}
              renderCompletions={(filterValue, valueType) => {
                return renderCompletions(filterValue, {valueType, onClear: clearPrompt, onCompact: compactPrompt});
              }}>
              {token => (
                <PromptToken token={token}>
                  {getIcon(token)}
                  {token.text}
                </PromptToken>
              )}
            </PromptTokenField>
            <PromptFieldToolbar>
              <div className={style({display: 'flex', gap: 8, alignItems: 'center'})}>
                <InsertMenuButton>
                  <AttachFileMenuItem />
                  <SubmenuTrigger>
                    <MenuItem>
                      <Prompt />
                      <Text>Commands</Text>
                    </MenuItem>
                    <Menu items={slashCommands.filter(item => item.kind === 'command')}>
                      {item => (
                        <CommandMenuItem
                          id={item.command}
                          onAction={item.command === '/clear' ? clearPrompt : compactPrompt}>
                          <Prompt />
                          <Text slot="label">{item.command}</Text>
                          <Text slot="description">{item.description}</Text>
                        </CommandMenuItem>
                      )}
                    </Menu>
                  </SubmenuTrigger>
                  <SubmenuTrigger>
                    <MenuItem>
                      <Plugin />
                      <Text>Skills</Text>
                    </MenuItem>
                    <Menu items={slashCommands.filter(item => item.kind === 'skill')}>
                      {item => (
                        <InsertTokenMenuItem
                          id={item.command}
                          token={{
                            type: 'token',
                            text: item.command,
                            value: {type: 'custom', anchor: '/', valueType: item.kind, data: item}
                          }}>
                          <Plugin />
                          <Text slot="label">{item.command}</Text>
                          <Text slot="description">{item.description}</Text>
                        </InsertTokenMenuItem>
                      )}
                    </Menu>
                  </SubmenuTrigger>
                  <SubmenuTrigger>
                    <MenuItem>
                      <Data />
                      <Text>Reference an object</Text>
                    </MenuItem>
                    <Menu items={objects}>
                      {item => (
                        <MenuSection>
                          <Header>
                            <Heading>{item.section}</Heading>
                          </Header>
                          <Collection items={item.items}>
                            {item => (
                              <InsertTokenMenuItem
                                id={item.title}
                                token={{
                                  type: 'token',
                                  text: item.title,
                                  value: {type: 'custom', anchor: '@', valueType: item.kind, data: item}
                                }}>
                                {item.title}
                              </InsertTokenMenuItem>
                            )}
                          </Collection>
                        </MenuSection>
                      )}
                    </Menu>
                  </SubmenuTrigger>
                </InsertMenuButton>
              </div>
              <div className={style({display: 'flex', gap: 8, alignItems: 'center'})}>
                <PromptFieldVoiceButton />
                <PromptFieldSubmitButton />
              </div>
            </PromptFieldToolbar>
          </PromptField>
        )}
      </VirtualizedStreamingChat>
    </div>
  );
}
```

## Installation

AI components are published as a separate package from `@react-spectrum/s2`.

```bash
npm install @react-spectrum/ai
```

## Prompt fields

Use `PromptField` as the foundation for allowing the user to submit a prompt. It manages an editable sequence of text and tokens, while `PromptTokenField` renders the input and `PromptFieldToolbar` contains its actions.

```tsx
import {useState} from 'react';
import {
  PromptField,
  PromptFieldSubmitButton,
  PromptFieldToolbar,
  PromptFieldValue,
  PromptTokenField
} from '@react-spectrum/ai';
import {style} from '@react-spectrum/s2/style' with {type: 'macro'};

function BasicPrompt(props) {
  let [value, setValue] = useState<PromptFieldValue>(() => new PromptFieldValue([]));

  return (
    /*- begin highlight -*/
    <PromptField
      {...props}
      
      value={value}
      onChange={setValue}
      onSubmit={value => {
        console.log(value.toString());
        setValue(new PromptFieldValue([]));
      }}
      styles={style({
        minWidth: 190,
        width: {
          default: 'full',
          size: {
            S: '50%'
          }
        }})({size: props.size})}>
      {/*- end highlight -*/}
      <PromptTokenField />
      <PromptFieldToolbar>
        <div style={{marginInlineStart: 'auto'}}>
          <PromptFieldSubmitButton />
        </div>
      </PromptFieldToolbar>
    </PromptField>
  );
}
```

### Suggestions and tokens

Suggestions can prefill a prompt, and a token field can offer context-aware completions such as mentions or commands.

```tsx
import {useState} from 'react';
import {
  InsertTokenMenuItem,
  MessageSuggestion,
  MessageSuggestionList,
  PromptField,
  PromptFieldSubmitButton,
  PromptFieldToolbar,
  PromptFieldValue,
  PromptTokenField
} from '@react-spectrum/ai';
import {style} from '@react-spectrum/s2/style' with {type: 'macro'};

/*- begin collapse -*/
let suggestionToken = style({
  outlineStyle: 'solid',
  outlineWidth: 1,
  outlineColor: 'transparent-overlay-1000/20',
  outlineOffset: -1,
  borderRadius: 'pill',
  paddingX: 8,
  paddingY: 0,
  fontSize: 'ui',
  display: 'inline-flex',
  verticalAlign: 'baseline'
});
/*- end collapse -*/

let people = ['Customers', 'Designers', 'Developers'];

let suggestions = [
  new PromptFieldValue([{type: 'text', text: 'Summarize this report'}]),
  new PromptFieldValue([
    {type: 'text', text: 'Draft a project brief for '},
    {
      type: 'token',
      text: 'Designers',
      value: {type: 'custom', anchor: '@', valueType: 'person', data: 'Designers'}
    }
  ]),
  new PromptFieldValue([{type: 'text', text: 'Find risks in this plan'}])
];

function PromptSuggestions() {
  let [value, setValue] = useState<PromptFieldValue>(() => new PromptFieldValue([]));

  return (
    <div style={{display: 'flex', flexDirection: 'column', gap: 16}}>
      <MessageSuggestionList title="Try asking">
        {suggestions.map((suggestion, i) => (
          <MessageSuggestion key={i} onPress={() => setValue(suggestion)}>
            {suggestion.segments.map((segment, j) =>
              segment.type === 'token' ? (
                <span key={j} className={suggestionToken}>{segment.text}</span>
              ) : (
                segment.text
              )
            )}
          </MessageSuggestion>
        ))}
      </MessageSuggestionList>
      <PromptField value={value} onChange={setValue} onSubmit={console.log}>
        <PromptTokenField
          completionTrigger={/(?<=^|\s)@/}
          /*- begin highlight -*/
          renderCompletions={filterValue =>
            people
              .filter(person => person.toLowerCase().includes(filterValue.slice(1).toLowerCase()))
              .map(person => (
                <InsertTokenMenuItem
                  key={person}
                  id={person}
                  token={{
                    type: 'token',
                    text: person,
                    value: {type: 'custom', anchor: '@', valueType: 'person', data: person}
                  }}>
                  {person}
                </InsertTokenMenuItem>
              ))
          }
          /*- end highlight -*/
          placeholder="Ask about @customers" />
        <PromptFieldToolbar>
          <div style={{marginInlineStart: 'auto'}}>
            <PromptFieldSubmitButton />
          </div>
        </PromptFieldToolbar>
      </PromptField>
    </div>
  );
}
```

### Attachments and actions

Use `PromptFieldAttachmentList` to render a preview of attached files the user has dragged onto the PromptField or added via the `InsertMenuButton` in the toolbar. Custom menu items and toolbar controls can be added as well.

```tsx
import {useState} from 'react';
import {
  Attachment,
  AttachmentPreview,
  AttachFileMenuItem,
  InsertMenuButton,
  InsertTextMenuItem,
  PromptField,
  PromptFieldAttachment,
  PromptFieldAttachmentList,
  PromptFieldSubmitButton,
  PromptFieldToolbar,
  PromptFieldVoiceButton,
  PromptFieldValue,
  PromptTokenField
} from '@react-spectrum/ai';
import {Text} from '@react-spectrum/s2';
import CommentText from '@react-spectrum/s2/icons/CommentText';

function PromptAttachments() {
  let [attachments, setAttachments] = useState<PromptFieldAttachment[]>([
    {id: '0', file: new File([], 'preview.png', {type: 'image/png'}), image: 'https://images.unsplash.com/photo-1705034598432-1694e203cdf3?q=80&w=600&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D'},
    {id: '1', file: new File([], 'notes.txt', {type: 'text/plain'}), image: ''}
  ]);

  return (
    <PromptField
      defaultValue={new PromptFieldValue([])}
      attachments={attachments}
      onAttachmentsChange={setAttachments}
      acceptedAttachmentTypes={['*/*']}>
      {/*- begin highlight -*/}
      <PromptFieldAttachmentList>
        {attachment => (
          <Attachment textValue={attachment.file.name}>
            <AttachmentPreview mimeType={attachment.file.type} src={attachment.image} />
          </Attachment>
        )}
      </PromptFieldAttachmentList>
      {/*- end highlight -*/}
      <PromptTokenField placeholder="Describe the image" />
      <PromptFieldToolbar>
        <InsertMenuButton>
          <AttachFileMenuItem />
          <InsertTextMenuItem id="summarize" text="Summarize this image">
            <CommentText />
            <Text>Summarize image</Text>
          </InsertTextMenuItem>
        </InsertMenuButton>
        <div style={{display: 'flex', gap: 8, alignItems: 'center'}}>
          <PromptFieldVoiceButton />
          <PromptFieldSubmitButton />
        </div>
      </PromptFieldToolbar>
    </PromptField>
  );
}
```

## Chat threads

Compose a conversation from `Chat`, `Thread`, `ResponseStatus`, `Alert`, and message components. The thread can be driven by a collection as messages arrive from your application.

```tsx
import {Alert, Chat, Thread, ThreadItem, UserMessage, ResponseStatus, ResponseStatusTitle, ResponseStatusPanel, ExecutionTrace, ExecutionTraceItem} from '@react-spectrum/ai';
import {prose} from '@react-spectrum/ai/style' with {type: 'macro'};
import {style} from '@react-spectrum/s2/style' with {type: 'macro'};

let messages = [
  {id: 1, type: 'user', text: 'Summarize the campaign results.'},
  {
    id: 2,
    type: 'status',
    status: 'success' as const,
    text: 'Response complete',
    steps: [
      {id: 1, label: 'Fetching campaign', status: 'success' as const, detail: 'Loaded campaign details and fetched engagement results from the database.'},
      {id: 2, label: 'Summarizing results', status: 'success' as const, detail: 'Created a full channel report and summarized the results.'}
    ]
  },
  {
    id: 3,
    type: 'assistant',
    text: 'Engagement increased 18% this month, led by email and social. See the full report for a channel breakdown.',
    content: (
      <>
        Engagement increased <strong>18%</strong> this month, led by email and social. See the{' '}
        <a href="#">full report</a> for a channel breakdown.
      </>
    )
  },
  {id: 4, type: 'user', text: 'Which channel performed best?'},
  {
    id: 5,
    type: 'assistant',
    text: 'Email drove the most conversions, with social close behind: Email with 4,200 conversions, Social with 3,100 conversions.',
    content: (
      <>
        <p>Email drove the most conversions, with social close behind:</p>
        <ul>
          <li>Email: 4,200 conversions</li>
          <li>Social: 3,100 conversions</li>
        </ul>
      </>
    )
  },
  {
    id: 6,
    type: 'alert',
    variant: 'notice' as const,
    text: "This summary may be incomplete. The connected data source hasn't synced in 2 hours."
  }
];

function BasicChat() {
  return (
    /*- begin highlight -*/
    <Chat
      /*- end highlight -*/
      styles={style({width: 'full'})}>
      <Thread
        items={messages}
        aria-label="Campaign discussion"
        styles={style({
          height: 350,
          overflowX: 'hidden',
          overflowY: 'auto',
          scrollPadding: 8
        })}>
        {message => {
          switch (message.type) {
            case 'user':
              return (
                <ThreadItem
                  textValue={message.text}
                  styles={style({display: 'flex', justifyContent: 'end'})}>
                  <UserMessage>{message.text}</UserMessage>
                </ThreadItem>
              );
            case 'assistant':
              return (
                <ThreadItem textValue={message.text}>
                  <div className={prose()}>{message.content}</div>
                </ThreadItem>
              );
            case 'status':
              return (
                <ThreadItem textValue={message.text}>
                  <ResponseStatus status={message.status}>
                    <ResponseStatusTitle>{message.text}</ResponseStatusTitle>
                    <ResponseStatusPanel>
                      <ExecutionTrace>
                        {message.steps?.map(step => (
                          <ExecutionTraceItem
                            key={step.id}
                            status={step.status}
                            detail={<p className={style({font: 'body-sm', margin: 0})}>{step.detail}</p>}>
                            {step.label}
                          </ExecutionTraceItem>
                        ))}
                      </ExecutionTrace>
                    </ResponseStatusPanel>
                  </ResponseStatus>
                </ThreadItem>
              );
            case 'alert':
              return (
                <ThreadItem textValue={message.text}>
                  <Alert variant={message.variant} >
                    {message.text}
                  </Alert>
                </ThreadItem>
              )
          }
        }}
      </Thread>
    </Chat>
  );
}
```

## Loaders

`PixelLoader` is the animated pixel icon shown inside `PromptField` and `ResponseStatus` while the assistant is working. It can also be used standalone anywhere an AI loading indicator is needed.

The `icon` prop accepts either a single icon, which loops forever, or a themed preset, which cycles through several icons, one per loop. Icons and presets are exported individually from `@react-spectrum/ai/loader`.

```tsx
import {PixelLoader} from '@react-spectrum/ai/loader';
import {style} from '@react-spectrum/s2/style' with {type: 'macro'};

function PresetLoader(props) {
  return (
    <div className={style({height: 40})} >
      {/*- begin highlight -*/}
      <PixelLoader
        {...props}
        
      />
      {/*- end highlight -*/}
    </div>
  );
}
```

### Usage

Use the `pixelLoader` prop on `ResponseStatusTitle` and `PromptTokenField` to display the pixel loader.

## ResponseStatus example

```tsx
import {cc} from '@react-spectrum/ai/loader';
import {ResponseStatus, ResponseStatusTitle} from '@react-spectrum/ai';
import {style} from '@react-spectrum/s2/style' with {type: 'macro'};

function LoadingStatus() {
  return (
    <div className={style({height: 40})}>
      <ResponseStatus status="pending">
        {/*- begin highlight -*/}
        <ResponseStatusTitle pixelLoader={cc}>Analyzing campaign data...</ResponseStatusTitle>
        {/*- end highlight -*/}
      </ResponseStatus>
    </div>
  );
}
```

## PromptField example

```tsx
import {pencil} from '@react-spectrum/ai/loader';
import {
  PromptField,
  PromptFieldSubmitButton,
  PromptFieldToolbar,
  PromptFieldValue,
  PromptTokenField
} from '@react-spectrum/ai';
import {useState} from 'react';

function GeneratingPrompt() {
  let [value, setValue] = useState<PromptFieldValue>(() => new PromptFieldValue([]));
  let [isGenerating, setIsGenerating] = useState(false);

  return (
    <PromptField
      value={value}
      onChange={setValue}
      isGenerating={isGenerating}
      onSubmit={() => {
        setValue(new PromptFieldValue([]));
        setIsGenerating(true);
        setTimeout(() => setIsGenerating(false), 3000);
      }}
      onStop={() => setIsGenerating(false)}>
      {/*- begin highlight -*/}
      <PromptTokenField placeholder="Ask a question" pixelLoader={pencil} />
      {/*- end highlight -*/}
      <PromptFieldToolbar>
        <div style={{marginInlineStart: 'auto'}}>
          <PromptFieldSubmitButton />
        </div>
      </PromptFieldToolbar>
    </PromptField>
  );
}
```

### Available icons

<AIIconsPageSearch/>

## API

```tsx
<Chat>
  <Thread>
    <ThreadItem />
  </Thread>
  <ThreadScrollButton />
  <PromptField />
</Chat>
```

## Chat

### ThreadScrollButton

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `children` | `ReactNode` | — |  |

## Thread

```tsx
<Thread>
  <ThreadItem>
    <UserMessage /> or <ResponseStatus /> or <MessageSuggestionList /> or assistant content
    <MessageSource /> and/or <MessageFeedback />
  </ThreadItem>
  <ThreadLoadMoreItem />
</Thread>
```

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `aria-label` | `string | undefined` | — | Defines a string value that labels the current element. |
| `aria-labelledby` | `string | undefined` | — | Identifies the element (or elements) that labels the current element. |
| `children` | `((item: T) => ReactNode) | ReactNode` | — | The contents of the collection. |
| `items` | `Iterable<T> | undefined` | — | Item objects in the collection. |
| `scrollEndThreshold` | `number | undefined` | 100 | The maximum distance in px from the bottom of the content for the viewport to be considered "near the end". While near the end, appended content and streaming size changes will keep the viewport pinned to the latest output. |
| `styles` | `StyleString | undefined` | — | Spectrum-defined styles, returned by the `style()` macro. |

### ThreadItem

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `allowsArrowNavigation` | `boolean | undefined` | — | Whether the row should support arrow key navigation even when the containing collection uses tab keyboard navigation. Allows users to navigate between rows with arrow keys while focus is on an interactive child element within the row. |
| `children` | `ReactNode` | — | The content to display in the ThreadItem. |
| `focusMode` | `"child" | "row" | undefined` | — | Whether the row or its first focusable child element should be focused when navigating to the row. Defaults to 'row'. |
| `id` | `Key | undefined` | — | The unique id of the item. |
| `isStreaming` | `boolean | undefined` | — | Whether or not the item's content is currently being streamed in. |
| `shouldAnnounceOnMount` | `boolean | undefined` | — | Announce textValue on mount even when isStreaming is provided. |
| `styles` | `StyleString | undefined` | — | Spectrum-defined styles, returned by the `style()` macro. |
| `textValue` | `string | undefined` | — | A string representation of the item's contents, used for features like typeahead. |

### ThreadLoadMoreItem

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `children` | `ReactNode` | — | The load more spinner to render when loading additional items. |
| `className` | `string | undefined` | 'react-aria-GridListLoadingIndicator' | The CSS [className](https://developer.mozilla.org/en-US/docs/Web/API/Element/className) for the element. |
| `dir` | `string | undefined` | — |  |
| `hidden` | `boolean | undefined` | — |  |
| `inert` | `boolean | undefined` | — |  |
| `isLoading` | `boolean | undefined` | — | Whether or not the loading spinner should be rendered or not. |
| `lang` | `string | undefined` | — |  |
| `onAnimationEnd` | `AnimationEventHandler<HTMLDivElement> | undefined` | — |  |
| `onAnimationEndCapture` | `AnimationEventHandler<HTMLDivElement> | undefined` | — |  |
| `onAnimationIteration` | `AnimationEventHandler<HTMLDivElement> | undefined` | — |  |
| `onAnimationIterationCapture` | `AnimationEventHandler<HTMLDivElement> | undefined` | — |  |
| `onAnimationStart` | `AnimationEventHandler<HTMLDivElement> | undefined` | — |  |
| `onAnimationStartCapture` | `AnimationEventHandler<HTMLDivElement> | undefined` | — |  |
| `onAuxClick` | `MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onAuxClickCapture` | `MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onClick` | `MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onClickCapture` | `MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onContextMenu` | `MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onContextMenuCapture` | `MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onDoubleClick` | `MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onDoubleClickCapture` | `MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onGotPointerCapture` | `PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onGotPointerCaptureCapture` | `PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onLoadMore` | `(() => any) | undefined` | — | Handler that is called when more items should be loaded, e.g. while scrolling near the bottom. |
| `onLostPointerCapture` | `PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onLostPointerCaptureCapture` | `PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseDown` | `MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseDownCapture` | `MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseEnter` | `MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseLeave` | `MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseMove` | `MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseMoveCapture` | `MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseOut` | `MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseOutCapture` | `MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseOver` | `MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseOverCapture` | `MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseUp` | `MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseUpCapture` | `MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerCancel` | `PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerCancelCapture` | `PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerDown` | `PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerDownCapture` | `PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerEnter` | `PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerLeave` | `PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerMove` | `PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerMoveCapture` | `PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerOut` | `PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerOutCapture` | `PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerOver` | `PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerOverCapture` | `PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerUp` | `PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerUpCapture` | `PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onScroll` | `UIEventHandler<HTMLDivElement> | undefined` | — |  |
| `onScrollCapture` | `UIEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTouchCancel` | `TouchEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTouchCancelCapture` | `TouchEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTouchEnd` | `TouchEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTouchEndCapture` | `TouchEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTouchMove` | `TouchEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTouchMoveCapture` | `TouchEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTouchStart` | `TouchEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTouchStartCapture` | `TouchEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTransitionCancel` | `TransitionEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTransitionCancelCapture` | `TransitionEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTransitionEnd` | `TransitionEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTransitionEndCapture` | `TransitionEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTransitionRun` | `TransitionEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTransitionRunCapture` | `TransitionEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTransitionStart` | `TransitionEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTransitionStartCapture` | `TransitionEventHandler<HTMLDivElement> | undefined` | — |  |
| `onWheel` | `WheelEventHandler<HTMLDivElement> | undefined` | — |  |
| `onWheelCapture` | `WheelEventHandler<HTMLDivElement> | undefined` | — |  |
| `render` | `DOMRenderFunction<"div", undefined> | undefined` | — | Overrides the default DOM element with a custom render function. This allows rendering existing components with built-in styles and behaviors such as router links, animation libraries, and pre-styled components. Requirements: - You must render the expected element type (e.g. if `<button>` is expected, you cannot render an   `<a>`). - Only a single root DOM element can be rendered (no fragments). - You must pass through props and ref to the underlying DOM element, merging with your own prop   as appropriate. |
| `scrollOffset` | `number | undefined` | 1 | The amount of offset from the bottom of your scrollable region that should trigger load more. Uses a percentage value relative to the scroll body's client height. Load more is then triggered when your current scroll position's distance from the bottom of the currently loaded list of items is less than or equal to the provided value. (e.g. 1 = 100% of the scroll region's height). |
| `style` | `CSSProperties | undefined` | — | The inline [style](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/style) for the element. |
| `translate` | `"no" | "yes" | undefined` | — |  |

### UserMessage

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `aria-describedby` | `string | undefined` | — | Identifies the element (or elements) that describes the object. |
| `aria-details` | `string | undefined` | — | Identifies the element (or elements) that provide a detailed, extended description for the object. |
| `aria-label` | `string | undefined` | — | Defines a string value that labels the current element. |
| `aria-labelledby` | `string | undefined` | — | Identifies the element (or elements) that labels the current element. |
| `children` | `ReactNode` | — | The contents of the user message bubble. |
| `id` | `string | undefined` | — | The element's unique identifier. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes/id). |
| `slot` | `string | null | undefined` | — | A slot name for the component. Slots allow the component to receive props from a parent component. An explicit `null` value indicates that the local props completely override all props received from a parent. |
| `styles` | `StyleString | undefined` | — | Spectrum-defined styles, returned by the `style()` macro. |

### ResponseStatus

```tsx
<ResponseStatus>
  <ResponseStatusTitle />
  <ResponseStatusPanel>
    <ExecutionTrace>
      <ExecutionTraceItem />
    </ExecutionTrace>
  </ResponseStatusPanel>
</ResponseStatus>
```

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `children` | `React.ReactNode` | — | The contents of the response status, consisting of a ResponseStatusTitle and ResponseStatusPanel. |
| `defaultExpanded` | `boolean | undefined` | — | Whether the disclosure is expanded by default (uncontrolled). |
| `id` | `Key | undefined` | — | An id for the disclosure when used within a DisclosureGroup, matching the id used in `expandedKeys`. |
| `isDisabled` | `boolean | undefined` | — | Whether the disclosure is disabled. |
| `isExpanded` | `boolean | undefined` | — | Whether the disclosure is expanded (controlled). |
| `onExpandedChange` | `((isExpanded: boolean) => void) | undefined` | — | Handler that is called when the disclosure's expanded state changes. |
| `slot` | `string | null | undefined` | — | A slot name for the component. Slots allow the component to receive props from a parent component. An explicit `null` value indicates that the local props completely override all props received from a parent. |
| `status` | `"failed" | "pending" | "success" | undefined` | 'pending' | The current status of the response. |
| `styles` | `StyleString | undefined` | — | Spectrum-defined styles, returned by the `style()` macro. |

#### ResponseStatusTitle

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `children` | `string` | — | The contents of the response status header. |
| `id` | `string | undefined` | — | The element's unique identifier. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes/id). |
| `level` | `number | undefined` | 3 | The heading level of the response status header. |
| `pixelLoader` | `Cell[] | Cell[][] | undefined` | — | Pixel loader icon or sequence to display. |
| `styles` | `StyleString | undefined` | — | Spectrum-defined styles, returned by the `style()` macro. |

#### ResponseStatusPanel

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `aria-describedby` | `string | undefined` | — | Identifies the element (or elements) that describes the object. |
| `aria-details` | `string | undefined` | — | Identifies the element (or elements) that provide a detailed, extended description for the object. |
| `aria-label` | `string | undefined` | — | Defines a string value that labels the current element. |
| `aria-labelledby` | `string | undefined` | — | Identifies the element (or elements) that labels the current element. |
| `children` | `React.ReactNode` | — |  |
| `dir` | `string | undefined` | — |  |
| `hidden` | `boolean | undefined` | — |  |
| `id` | `string | undefined` | — | The element's unique identifier. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes/id). |
| `inert` | `boolean | undefined` | — |  |
| `label` | `React.ReactNode` | — | The content to display as the label. |
| `labelElementType` | `React.ElementType | undefined` | 'label' | The HTML element used to render the label, e.g. 'label', or 'span'. |
| `lang` | `string | undefined` | — |  |
| `onAnimationEnd` | `React.AnimationEventHandler<HTMLDivElement> | undefined` | — |  |
| `onAnimationEndCapture` | `React.AnimationEventHandler<HTMLDivElement> | undefined` | — |  |
| `onAnimationIteration` | `React.AnimationEventHandler<HTMLDivElement> | undefined` | — |  |
| `onAnimationIterationCapture` | `React.AnimationEventHandler<HTMLDivElement> | undefined` | — |  |
| `onAnimationStart` | `React.AnimationEventHandler<HTMLDivElement> | undefined` | — |  |
| `onAnimationStartCapture` | `React.AnimationEventHandler<HTMLDivElement> | undefined` | — |  |
| `onAuxClick` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onAuxClickCapture` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onClick` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onClickCapture` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onContextMenu` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onContextMenuCapture` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onDoubleClick` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onDoubleClickCapture` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onGotPointerCapture` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onGotPointerCaptureCapture` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onLostPointerCapture` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onLostPointerCaptureCapture` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseDown` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseDownCapture` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseEnter` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseLeave` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseMove` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseMoveCapture` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseOut` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseOutCapture` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseOver` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseOverCapture` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseUp` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseUpCapture` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerCancel` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerCancelCapture` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerDown` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerDownCapture` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerEnter` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerLeave` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerMove` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerMoveCapture` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerOut` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerOutCapture` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerOver` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerOverCapture` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerUp` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerUpCapture` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onScroll` | `React.UIEventHandler<HTMLDivElement> | undefined` | — |  |
| `onScrollCapture` | `React.UIEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTouchCancel` | `React.TouchEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTouchCancelCapture` | `React.TouchEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTouchEnd` | `React.TouchEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTouchEndCapture` | `React.TouchEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTouchMove` | `React.TouchEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTouchMoveCapture` | `React.TouchEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTouchStart` | `React.TouchEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTouchStartCapture` | `React.TouchEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTransitionCancel` | `React.TransitionEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTransitionCancelCapture` | `React.TransitionEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTransitionEnd` | `React.TransitionEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTransitionEndCapture` | `React.TransitionEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTransitionRun` | `React.TransitionEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTransitionRunCapture` | `React.TransitionEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTransitionStart` | `React.TransitionEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTransitionStartCapture` | `React.TransitionEventHandler<HTMLDivElement> | undefined` | — |  |
| `onWheel` | `React.WheelEventHandler<HTMLDivElement> | undefined` | — |  |
| `onWheelCapture` | `React.WheelEventHandler<HTMLDivElement> | undefined` | — |  |
| `role` | `"group" | "region" | undefined` | 'group' | The accessibility role for the disclosure's panel. |
| `styles` | `StyleString | undefined` | — | Spectrum-defined styles, returned by the `style()` macro. |
| `translate` | `"no" | "yes" | undefined` | — |  |

#### ExecutionTrace

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `aria-describedby` | `string | undefined` | — | Identifies the element (or elements) that describes the object. |
| `aria-details` | `string | undefined` | — | Identifies the element (or elements) that provide a detailed, extended description for the object. |
| `aria-label` | `string | undefined` | — | Defines a string value that labels the current element. |
| `aria-labelledby` | `string | undefined` | — | Identifies the element (or elements) that labels the current element. |
| `children` | `React.ReactNode` | — | The ExecutionTraceItem elements to render as a timeline. Typically placed inside a ResponseStatusPanel. |
| `id` | `string | undefined` | — | The element's unique identifier. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes/id). |
| `styles` | `StyleString | undefined` | — | Spectrum-defined styles, returned by the `style()` macro. |

#### ExecutionTraceItem

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `aria-describedby` | `string | undefined` | — | Identifies the element (or elements) that describes the object. |
| `aria-details` | `string | undefined` | — | Identifies the element (or elements) that provide a detailed, extended description for the object. |
| `aria-label` | `string | undefined` | — | Defines a string value that labels the current element. |
| `aria-labelledby` | `string | undefined` | — | Identifies the element (or elements) that labels the current element. |
| `children` | `string` | — | The label describing the step. |
| `detail` | `React.ReactNode` | — | Additional detail revealed when the step is expanded, such as tool call input or output. If omitted, the row is static and cannot be expanded. |
| `detailMaxHeight` | `number | undefined` | 120 | Maximum height for the detail panel. |
| `icon` | `React.ReactNode` | — | An icon shown at the leading edge of the row. If omitted, a checkmark is rendered by default. |
| `id` | `string | undefined` | — | The element's unique identifier. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes/id). |
| `status` | `"failed" | "pending" | "success" | undefined` | — | The status of this step. |
| `styles` | `StyleString | undefined` | — | Spectrum-defined styles, returned by the `style()` macro. |

### Alert

### MessageSuggestionList

```tsx
<MessageSuggestionList>
  <MessageSuggestion />
</MessageSuggestionList>
```

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `aria-describedby` | `string | undefined` | — | Identifies the element (or elements) that describes the object. |
| `aria-details` | `string | undefined` | — | Identifies the element (or elements) that provide a detailed, extended description for the object. |
| `aria-label` | `string | undefined` | — | Defines a string value that labels the current element. |
| `aria-labelledby` | `string | undefined` | — | Identifies the element (or elements) that labels the current element. |
| `children` | `ReactNode` | — | The MessageSuggestion children to display. |
| `id` | `string | undefined` | — | The element's unique identifier. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes/id). |
| `size` | `"L" | "M" | "S" | "XL" | undefined` | — | The size of hte Buttons within the MessageSuggestionList. |
| `slot` | `string | null | undefined` | — | A slot name for the component. Slots allow the component to receive props from a parent component. An explicit `null` value indicates that the local props completely override all props received from a parent. |
| `styles` | `StyleString | undefined` | — | Spectrum-defined styles, returned by the `style()` macro. |
| `title` | `string` | — | Heading displayed above the suggestions. |

#### MessageSuggestion

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `aria-controls` | `string | undefined` | — | Identifies the element (or elements) whose contents or presence are controlled by the current element. |
| `aria-current` | `boolean | "true" | "false" | "date" | "location" | "page" | "step" | "time" | undefined` | — | Indicates whether this element represents the current item within a container or set of related elements. |
| `aria-describedby` | `string | undefined` | — | Identifies the element (or elements) that describes the object. |
| `aria-details` | `string | undefined` | — | Identifies the element (or elements) that provide a detailed, extended description for the object. |
| `aria-disabled` | `boolean | "true" | "false" | undefined` | — | Indicates whether the element is disabled to users of assistive technology. |
| `aria-expanded` | `boolean | "true" | "false" | undefined` | — | Indicates whether the element, or another grouping element it controls, is currently expanded or collapsed. |
| `aria-haspopup` | `boolean | "true" | "false" | "dialog" | "grid" | "listbox" | "menu" | "tree" | undefined` | — | Indicates the availability and type of interactive popup element, such as menu or dialog, that can be triggered by an element. |
| `aria-label` | `string | undefined` | — | Defines a string value that labels the current element. |
| `aria-labelledby` | `string | undefined` | — | Identifies the element (or elements) that labels the current element. |
| `aria-pressed` | `boolean | "true" | "false" | "mixed" | undefined` | — | Indicates the current "pressed" state of toggle buttons. |
| `autoFocus` | `boolean | undefined` | — | Whether the element should receive focus on render. |
| `children` | `ReactNode` | — | The text content of the suggestion. |
| `excludeFromTabOrder` | `boolean | undefined` | — | Whether to exclude the element from the sequential tab order. If true, the element will not be focusable via the keyboard by tabbing. This should be avoided except in rare scenarios where an alternative means of accessing the element or its functionality via the keyboard is available. |
| `form` | `string | undefined` | — | The `<form>` element to associate the button with. The value of this attribute must be the id of a `<form>` in the same document. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/button#form). |
| `formAction` | `string | ((formData: FormData) => void | Promise<void>) | undefined` | — | The URL that processes the information submitted by the button. Overrides the action attribute of the button's form owner. |
| `formEncType` | `string | undefined` | — | Indicates how to encode the form data that is submitted. |
| `formMethod` | `string | undefined` | — | Indicates the HTTP method used to submit the form. |
| `formNoValidate` | `boolean | undefined` | — | Indicates that the form is not to be validated when it is submitted. |
| `formTarget` | `string | undefined` | — | Overrides the target attribute of the button's form owner. |
| `id` | `string | undefined` | — | The element's unique identifier. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes/id). |
| `name` | `string | undefined` | — | Submitted as a pair with the button's value as part of the form data. |
| `onBlur` | `((e: FocusEvent<Element>) => void) | undefined` | — | Handler that is called when the element loses focus. |
| `onFocus` | `((e: FocusEvent<Element>) => void) | undefined` | — | Handler that is called when the element receives focus. |
| `onFocusChange` | `((isFocused: boolean) => void) | undefined` | — | Handler that is called when the element's focus status changes. |
| `onHoverChange` | `((isHovering: boolean) => void) | undefined` | — | Handler that is called when the hover state changes. |
| `onHoverEnd` | `((e: HoverEvent) => void) | undefined` | — | Handler that is called when a hover interaction ends. |
| `onHoverStart` | `((e: HoverEvent) => void) | undefined` | — | Handler that is called when a hover interaction starts. |
| `onKeyDown` | `((e: KeyboardEvent) => void) | undefined` | — | Handler that is called when a key is pressed. |
| `onKeyUp` | `((e: KeyboardEvent) => void) | undefined` | — | Handler that is called when a key is released. |
| `onPress` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when the press is released over the target. |
| `onPressChange` | `((isPressed: boolean) => void) | undefined` | — | Handler that is called when the press state changes. |
| `onPressEnd` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when a press interaction ends, either over the target or when the pointer leaves the target. |
| `onPressStart` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when a press interaction starts. |
| `onPressUp` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when a press is released over the target, regardless of whether it started on the target or not. |
| `preventFocusOnPress` | `boolean | undefined` | — | Whether to prevent focus from moving to the button when pressing it. Caution, this can make the button inaccessible and should only be used when alternative keyboard interaction is provided, such as ComboBox's MenuTrigger or a NumberField's increment/decrement control. |
| `size` | `"L" | "M" | "S" | "XL" | undefined` | 'M' | The size of the MessageSuggestion. |
| `slot` | `string | null | undefined` | — | A slot name for the component. Slots allow the component to receive props from a parent component. An explicit `null` value indicates that the local props completely override all props received from a parent. |
| `styles` | `StyleString | undefined` | — | Spectrum-defined styles, returned by the `style()` macro. |
| `type` | `"button" | "reset" | "submit" | undefined` | 'button' | The behavior of the button when used in an HTML form. |
| `value` | `string | undefined` | — | The value associated with the button's name when it's submitted with the form data. |

### MessageFeedback

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `aria-describedby` | `string | undefined` | — | Identifies the element (or elements) that describes the object. |
| `aria-details` | `string | undefined` | — | Identifies the element (or elements) that provide a detailed, extended description for the object. |
| `aria-label` | `string | undefined` | — | Defines a string value that labels the current element. |
| `aria-labelledby` | `string | undefined` | — | Identifies the element (or elements) that labels the current element. |
| `defaultValue` | `MessageFeedbackValue | undefined` | — | The default feedback value (uncontrolled). |
| `id` | `string | undefined` | — | The element's unique identifier. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes/id). |
| `isDisabled` | `boolean | undefined` | — | Whether the feedback controls are disabled. |
| `onChange` | `((value: MessageFeedbackValue) => void) | undefined` | — | Called when the selection changes, including when toggled off (value=null). |
| `size` | `"L" | "M" | "S" | "XL" | "XS" | undefined` | 'M' | Size of the buttons. |
| `slot` | `string | null | undefined` | — | A slot name for the component. Slots allow the component to receive props from a parent component. An explicit `null` value indicates that the local props completely override all props received from a parent. |
| `styles` | `StylesPropWithHeight | undefined` | — | Spectrum-defined styles, returned by the `style()` macro. |
| `thumbDownLabel` | `string | undefined` | — | Accessible label for the thumbs down button. |
| `thumbUpLabel` | `string | undefined` | — | Accessible label for the thumbs up button. |
| `value` | `MessageFeedbackValue | undefined` | — | The selected feedback value (controlled). |

### MessageSource

```tsx
<MessageSource>
  <SourceList>
    <SourceListItem />
  </SourceList>
</MessageSource>
```

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `children` | `React.ReactNode` | — | The contents of the disclosure, consisting of a DisclosureTitle and DisclosurePanel. |
| `defaultExpanded` | `boolean | undefined` | — | Whether the disclosure is expanded by default (uncontrolled). |
| `density` | `"compact" | "regular" | "spacious" | undefined` | 'regular' | The amount of space between the disclosures. |
| `id` | `Key | undefined` | — | An id for the disclosure when used within a DisclosureGroup, matching the id used in `expandedKeys`. |
| `isDisabled` | `boolean | undefined` | — | Whether the disclosure is disabled. |
| `isExpanded` | `boolean | undefined` | — | Whether the disclosure is expanded (controlled). |
| `label` | `string` | — |  |
| `onExpandedChange` | `((isExpanded: boolean) => void) | undefined` | — | Handler that is called when the disclosure's expanded state changes. |
| `size` | `"L" | "M" | "S" | "XL" | undefined` | 'M' | The size of the disclosure. |
| `slot` | `string | null | undefined` | — | A slot name for the component. Slots allow the component to receive props from a parent component. An explicit `null` value indicates that the local props completely override all props received from a parent. |
| `styles` | `StylesProp | undefined` | — | Spectrum-defined styles, returned by the `style()` macro. |

#### SourceList

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `aria-describedby` | `string | undefined` | — | Identifies the element (or elements) that describes the object. |
| `aria-details` | `string | undefined` | — | Identifies the element (or elements) that provide a detailed, extended description for the object. |
| `aria-label` | `string | undefined` | — | Defines a string value that labels the current element. |
| `aria-labelledby` | `string | undefined` | — | Identifies the element (or elements) that labels the current element. |
| `children` | `React.ReactNode` | — |  |
| `dir` | `string | undefined` | — |  |
| `hidden` | `boolean | undefined` | — |  |
| `id` | `string | undefined` | — | The element's unique identifier. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes/id). |
| `inert` | `boolean | undefined` | — |  |
| `label` | `React.ReactNode` | — | The content to display as the label. |
| `labelElementType` | `React.ElementType | undefined` | 'label' | The HTML element used to render the label, e.g. 'label', or 'span'. |
| `lang` | `string | undefined` | — |  |
| `onAnimationEnd` | `React.AnimationEventHandler<HTMLDivElement> | undefined` | — |  |
| `onAnimationEndCapture` | `React.AnimationEventHandler<HTMLDivElement> | undefined` | — |  |
| `onAnimationIteration` | `React.AnimationEventHandler<HTMLDivElement> | undefined` | — |  |
| `onAnimationIterationCapture` | `React.AnimationEventHandler<HTMLDivElement> | undefined` | — |  |
| `onAnimationStart` | `React.AnimationEventHandler<HTMLDivElement> | undefined` | — |  |
| `onAnimationStartCapture` | `React.AnimationEventHandler<HTMLDivElement> | undefined` | — |  |
| `onAuxClick` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onAuxClickCapture` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onClick` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onClickCapture` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onContextMenu` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onContextMenuCapture` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onDoubleClick` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onDoubleClickCapture` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onGotPointerCapture` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onGotPointerCaptureCapture` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onLostPointerCapture` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onLostPointerCaptureCapture` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseDown` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseDownCapture` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseEnter` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseLeave` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseMove` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseMoveCapture` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseOut` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseOutCapture` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseOver` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseOverCapture` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseUp` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onMouseUpCapture` | `React.MouseEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerCancel` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerCancelCapture` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerDown` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerDownCapture` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerEnter` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerLeave` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerMove` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerMoveCapture` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerOut` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerOutCapture` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerOver` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerOverCapture` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerUp` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onPointerUpCapture` | `React.PointerEventHandler<HTMLDivElement> | undefined` | — |  |
| `onScroll` | `React.UIEventHandler<HTMLDivElement> | undefined` | — |  |
| `onScrollCapture` | `React.UIEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTouchCancel` | `React.TouchEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTouchCancelCapture` | `React.TouchEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTouchEnd` | `React.TouchEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTouchEndCapture` | `React.TouchEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTouchMove` | `React.TouchEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTouchMoveCapture` | `React.TouchEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTouchStart` | `React.TouchEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTouchStartCapture` | `React.TouchEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTransitionCancel` | `React.TransitionEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTransitionCancelCapture` | `React.TransitionEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTransitionEnd` | `React.TransitionEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTransitionEndCapture` | `React.TransitionEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTransitionRun` | `React.TransitionEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTransitionRunCapture` | `React.TransitionEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTransitionStart` | `React.TransitionEventHandler<HTMLDivElement> | undefined` | — |  |
| `onTransitionStartCapture` | `React.TransitionEventHandler<HTMLDivElement> | undefined` | — |  |
| `onWheel` | `React.WheelEventHandler<HTMLDivElement> | undefined` | — |  |
| `onWheelCapture` | `React.WheelEventHandler<HTMLDivElement> | undefined` | — |  |
| `role` | `"group" | "region" | undefined` | 'group' | The accessibility role for the disclosure's panel. |
| `translate` | `"no" | "yes" | undefined` | — |  |
| `UNSAFE_className` | `UnsafeClassName | undefined` | — | Sets the CSS [className](https://developer.mozilla.org/en-US/docs/Web/API/Element/className) for the element. Only use as a **last resort**. Use the `style` macro via the `styles` prop instead. |
| `UNSAFE_style` | `React.CSSProperties | undefined` | — | Sets inline [style](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/style) for the element. Only use as a **last resort**. Use the `style` macro via the `styles` prop instead. |

#### SourceListItem

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `aria-describedby` | `string | undefined` | — | Identifies the element (or elements) that describes the object. |
| `aria-details` | `string | undefined` | — | Identifies the element (or elements) that provide a detailed, extended description for the object. |
| `aria-label` | `string | undefined` | — | Defines a string value that labels the current element. |
| `aria-labelledby` | `string | undefined` | — | Identifies the element (or elements) that labels the current element. |
| `autoFocus` | `boolean | undefined` | — | Whether the element should receive focus on render. |
| `children` | `React.ReactNode` | — | The content of the source list item. |
| `download` | `boolean | string | undefined` | — | Causes the browser to download the linked URL. A string may be provided to suggest a file name. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/a#download). |
| `href` | `string | undefined` | — | A URL to link to. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/a#href). |
| `hrefLang` | `string | undefined` | — | Hints at the human language of the linked URL. See[MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/a#hreflang). |
| `id` | `string | undefined` | — | The element's unique identifier. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes/id). |
| `isDisabled` | `boolean | undefined` | — | Whether the link is disabled. |
| `onBlur` | `((e: React.FocusEvent<Element>) => void) | undefined` | — | Handler that is called when the element loses focus. |
| `onFocus` | `((e: React.FocusEvent<Element>) => void) | undefined` | — | Handler that is called when the element receives focus. |
| `onFocusChange` | `((isFocused: boolean) => void) | undefined` | — | Handler that is called when the element's focus status changes. |
| `onHoverChange` | `((isHovering: boolean) => void) | undefined` | — | Handler that is called when the hover state changes. |
| `onHoverEnd` | `((e: HoverEvent) => void) | undefined` | — | Handler that is called when a hover interaction ends. |
| `onHoverStart` | `((e: HoverEvent) => void) | undefined` | — | Handler that is called when a hover interaction starts. |
| `onKeyDown` | `((e: KeyboardEvent) => void) | undefined` | — | Handler that is called when a key is pressed. |
| `onKeyUp` | `((e: KeyboardEvent) => void) | undefined` | — | Handler that is called when a key is released. |
| `onPress` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when the press is released over the target. |
| `onPressChange` | `((isPressed: boolean) => void) | undefined` | — | Handler that is called when the press state changes. |
| `onPressEnd` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when a press interaction ends, either over the target or when the pointer leaves the target. |
| `onPressStart` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when a press interaction starts. |
| `onPressUp` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when a press is released over the target, regardless of whether it started on the target or not. |
| `ping` | `string | undefined` | — | A space-separated list of URLs to ping when the link is followed. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/a#ping). |
| `referrerPolicy` | `React.HTMLAttributeReferrerPolicy | undefined` | — | How much of the referrer to send when following the link. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/a#referrerpolicy). |
| `rel` | `string | undefined` | — | The relationship between the linked resource and the current page. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Attributes/rel). |
| `routerOptions` | `undefined` | — | Options for the configured client side router. |
| `slot` | `string | null | undefined` | — | A slot name for the component. Slots allow the component to receive props from a parent component. An explicit `null` value indicates that the local props completely override all props received from a parent. |
| `styles` | `StyleString | undefined` | — | Spectrum-defined styles, returned by the `style()` macro. |
| `target` | `React.HTMLAttributeAnchorTarget | undefined` | — | The target window for the link. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/a#target). |

## PromptField

```tsx
<PromptField>
  <PromptFieldAttachmentList />
  <PromptTokenField />
  <PromptFieldToolbar />
</PromptField>
```

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `acceptedAttachmentTypes` | `string[] | undefined` | — |  |
| `aiDisclaimer` | `ReactNode` | — | Custom text for the AI usage disclaimer shown below the prompt field. |
| `attachments` | `PromptFieldAttachment[] | undefined` | — |  |
| `brandColor` | `string | undefined` | — |  |
| `children` | `ReactNode` | — |  |
| `defaultAttachments` | `PromptFieldAttachment[] | undefined` | — |  |
| `defaultValue` | `PromptFieldValue | undefined` | — |  |
| `isGenerating` | `boolean | undefined` | — |  |
| `onAddAttachments` | `((attachments: PromptFieldAttachment[]) => void) | undefined` | — |  |
| `onAITermsPress` | `(() => void) | undefined` | — |  |
| `onAttachmentsChange` | `((attachments: PromptFieldAttachment[]) => void) | undefined` | — |  |
| `onChange` | `((value: PromptFieldValue) => void) | undefined` | — |  |
| `onRemoveAttachments` | `((attachments: PromptFieldAttachment[]) => void) | undefined` | — |  |
| `onStop` | `(() => void) | undefined` | — |  |
| `onSubmit` | `((prompt: PromptFieldValue, attachments: PromptFieldAttachment[]) => void) | undefined` | — |  |
| `size` | `"M" | "S" | undefined` | 'M' | The size of the PromptField. |
| `styles` | `StyleString | undefined` | — |  |
| `value` | `PromptFieldValue | undefined` | — |  |
| `variant` | `"balanced" | "prominent" | "subtle" | undefined` | 'balanced' |  |

### PromptFieldAttachmentList

```tsx
<PromptFieldAttachmentList>
  {attachment => (
    <Attachment>
      <AttachmentPreview />
    </Attachment>
  )}
</PromptFieldAttachmentList>
```

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `aria-describedby` | `string | undefined` | — | Identifies the element (or elements) that describes the object. |
| `aria-details` | `string | undefined` | — | Identifies the element (or elements) that provide a detailed, extended description for the object. |
| `aria-label` | `string | undefined` | — | Defines a string value that labels the current element. |
| `aria-labelledby` | `string | undefined` | — | Identifies the element (or elements) that labels the current element. |
| `children` | `((attachment: PromptFieldAttachment) => React.ReactNode) | undefined` | — |  |
| `dependencies` | `readonly any[] | undefined` | — | Values that should invalidate the item cache when using dynamic collections. |
| `disabledKeys` | `Iterable<Key> | undefined` | — | The item keys that are disabled. These items cannot be selected, focused, or otherwise interacted with. |
| `id` | `string | undefined` | — | The element's unique identifier. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Global_attributes/id). |
| `items` | `Iterable<PromptFieldAttachment> | undefined` | — | Item objects in the collection. |
| `onRemove` | `((keys: Set<Key>) => void) | undefined` | — | Handler that is called when a user deletes a tag. |
| `slot` | `string | null | undefined` | — | A slot name for the component. Slots allow the component to receive props from a parent component. An explicit `null` value indicates that the local props completely override all props received from a parent. |
| `styles` | `StyleString | undefined` | — | Spectrum-defined styles, returned by the `style()` macro. |

#### Attachment

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `aria-describedby` | `string | undefined` | — | Identifies the element (or elements) that describes the object. |
| `aria-details` | `string | undefined` | — | Identifies the element (or elements) that provide a detailed, extended description for the object. |
| `aria-label` | `string | undefined` | — | Defines a string value that labels the current element. |
| `aria-labelledby` | `string | undefined` | — | Identifies the element (or elements) that labels the current element. |
| `children` | `ReactNode` | — | The children of the Attachment. |
| `density` | `"compact" | "regular" | "spacious" | undefined` | 'regular' | The amount of internal padding within the Card. |
| `download` | `boolean | string | undefined` | — | Causes the browser to download the linked URL. A string may be provided to suggest a file name. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/a#download). |
| `href` | `string | undefined` | — | A URL to link to. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/a#href). |
| `hrefLang` | `string | undefined` | — | Hints at the human language of the linked URL. See[MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/a#hreflang). |
| `id` | `Key | undefined` | — | The unique id of the item. |
| `isDisabled` | `boolean | undefined` | — | Whether the item is disabled. |
| `isInvalid` | `boolean | undefined` | — | Whether the attachment has an error. |
| `onAction` | `(() => void) | undefined` | — | Handler that is called when a user performs an action on the item. The exact user event depends on the collection's `selectionBehavior` prop and the interaction modality. |
| `onPress` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when the press is released over the target. |
| `onPressChange` | `((isPressed: boolean) => void) | undefined` | — | Handler that is called when the press state changes. |
| `onPressEnd` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when a press interaction ends, either over the target or when the pointer leaves the target. |
| `onPressStart` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when a press interaction starts. |
| `onPressUp` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when a press is released over the target, regardless of whether it started on the target or not. |
| `ping` | `string | undefined` | — | A space-separated list of URLs to ping when the link is followed. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/a#ping). |
| `referrerPolicy` | `HTMLAttributeReferrerPolicy | undefined` | — | How much of the referrer to send when following the link. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/a#referrerpolicy). |
| `rel` | `string | undefined` | — | The relationship between the linked resource and the current page. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Attributes/rel). |
| `render` | `DOMRenderFunction<"div", TagRenderProps> | undefined` | — | Overrides the default DOM element with a custom render function. This allows rendering existing components with built-in styles and behaviors such as router links, animation libraries, and pre-styled components. Requirements: - You must render the expected element type (e.g. if `<button>` is expected, you cannot render an   `<a>`). - Only a single root DOM element can be rendered (no fragments). - You must pass through props and ref to the underlying DOM element, merging with your own prop   as appropriate. |
| `routerOptions` | `undefined` | — | Options for the configured client side router. |
| `size` | `"L" | "M" | "S" | "XL" | "XS" | undefined` | 'M' | The size of the Card. |
| `styles` | `StyleString | undefined` | — | Spectrum-defined styles, returned by the `style()` macro. |
| `target` | `HTMLAttributeAnchorTarget | undefined` | — | The target window for the link. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/a#target). |
| `textValue` | `string | undefined` | — | A string representation of the item's contents, used for features like typeahead. |
| `uploadProgress` | `number | undefined` | — |  |
| `value` | `object | undefined` | — | The object value that this item represents. When using dynamic collections, this is set automatically. |
| `variant` | `"primary" | "quiet" | "secondary" | "tertiary" | undefined` | 'primary' | The visual style of the Card. |

#### AttachmentPreview

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `alt` | `string | undefined` | — | Accessible alt text for the image. |
| `crossOrigin` | `"anonymous" | "use-credentials" | undefined` | — | Indicates if the fetching of the image must be done using a CORS request. [See MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Attributes/crossorigin). |
| `decoding` | `"async" | "auto" | "sync" | undefined` | — | Whether the browser should decode images synchronously or asynchronously. [See MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/img#decoding). |
| `fetchPriority` | `"auto" | "high" | "low" | undefined` | — | Provides a hint of the relative priority to use when fetching the image. [See MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/img#fetchpriority). |
| `group` | `ImageGroup | undefined` | — | A group of images to coordinate between, matching the group passed to the `<ImageCoordinator>` component. If not provided, the default image group is used. |
| `height` | `number | undefined` | — | The intrinsic height of the image. [See MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/img#height). |
| `itemProp` | `string | undefined` | — | Associates the image with a microdata object. See [MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Global_attributes/itemprop). |
| `loading` | `"eager" | "lazy" | undefined` | — | Whether the image should be loaded immediately or lazily when scrolled into view. [See MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/img#loading). |
| `mimeType` | `string` | — |  |
| `referrerPolicy` | `HTMLAttributeReferrerPolicy | undefined` | — | A string indicating which referrer to use when fetching the resource. [See MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/img#referrerpolicy). |
| `renderError` | `(() => ReactNode) | undefined` | — | A function that is called to render a fallback when the image fails to load. |
| `slot` | `string | null | undefined` | — | A slot name for the component. Slots allow the component to receive props from a parent component. An explicit `null` value indicates that the local props completely override all props received from a parent. |
| `src` | `string | ImageSource[] | undefined` | — | The URL of the image or a list of conditional sources. |
| `styles` | `StyleString | undefined` | — | Spectrum-defined styles, returned by the `style()` macro. |
| `UNSAFE_className` | `UnsafeClassName | undefined` | — | Sets the CSS [className](https://developer.mozilla.org/en-US/docs/Web/API/Element/className) for the element. Only use as a **last resort**. Use the `style` macro via the `styles` prop instead. |
| `UNSAFE_style` | `CSSProperties | undefined` | — | Sets inline [style](https://developer.mozilla.org/en-US/docs/Web/API/HTMLElement/style) for the element. Only use as a **last resort**. Use the `style` macro via the `styles` prop instead. |
| `width` | `number | undefined` | — | The intrinsic width of the image. [See MDN](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/img#width). |

### PromptTokenField

```tsx
<PromptTokenField>
  {token => <PromptToken token={token} />}
</PromptTokenField>
```

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `children` | `((segment: TokenSegment<PromptFieldTokenValue>) => React.ReactElement) | undefined` | — |  |
| `completionTrigger` | `RegExp | undefined` | — |  |
| `menuWidth` | `number | undefined` | — |  |
| `onKeyDown` | `((e: React.KeyboardEvent<HTMLDivElement>) => void) | undefined` | — |  |
| `pixelLoader` | `Cell[] | Cell[][] | undefined` | — |  |
| `placeholder` | `string | undefined` | — |  |
| `renderCompletions` | `((filterValue: string, valueType: string | null) => Promise<React.ReactNode[] | null> | null) | React.ReactNode[] | undefined` | — |  |
| `shouldAnimatePixelLoader` | `boolean | undefined` | — |  |

#### PromptToken

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `children` | `ReactNode` | — |  |
| `dir` | `string | undefined` | — |  |
| `hidden` | `boolean | undefined` | — |  |
| `inert` | `boolean | undefined` | — |  |
| `lang` | `string | undefined` | — |  |
| `onAnimationEnd` | `AnimationEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onAnimationEndCapture` | `AnimationEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onAnimationIteration` | `AnimationEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onAnimationIterationCapture` | `AnimationEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onAnimationStart` | `AnimationEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onAnimationStartCapture` | `AnimationEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onAuxClick` | `MouseEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onAuxClickCapture` | `MouseEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onClick` | `MouseEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onClickCapture` | `MouseEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onContextMenu` | `MouseEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onContextMenuCapture` | `MouseEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onDoubleClick` | `MouseEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onDoubleClickCapture` | `MouseEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onGotPointerCapture` | `PointerEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onGotPointerCaptureCapture` | `PointerEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onLostPointerCapture` | `PointerEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onLostPointerCaptureCapture` | `PointerEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onMouseDown` | `MouseEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onMouseDownCapture` | `MouseEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onMouseEnter` | `MouseEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onMouseLeave` | `MouseEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onMouseMove` | `MouseEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onMouseMoveCapture` | `MouseEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onMouseOut` | `MouseEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onMouseOutCapture` | `MouseEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onMouseOver` | `MouseEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onMouseOverCapture` | `MouseEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onMouseUp` | `MouseEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onMouseUpCapture` | `MouseEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onPointerCancel` | `PointerEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onPointerCancelCapture` | `PointerEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onPointerDown` | `PointerEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onPointerDownCapture` | `PointerEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onPointerEnter` | `PointerEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onPointerLeave` | `PointerEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onPointerMove` | `PointerEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onPointerMoveCapture` | `PointerEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onPointerOut` | `PointerEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onPointerOutCapture` | `PointerEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onPointerOver` | `PointerEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onPointerOverCapture` | `PointerEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onPointerUp` | `PointerEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onPointerUpCapture` | `PointerEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onScroll` | `UIEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onScrollCapture` | `UIEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onTouchCancel` | `TouchEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onTouchCancelCapture` | `TouchEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onTouchEnd` | `TouchEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onTouchEndCapture` | `TouchEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onTouchMove` | `TouchEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onTouchMoveCapture` | `TouchEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onTouchStart` | `TouchEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onTouchStartCapture` | `TouchEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onTransitionCancel` | `TransitionEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onTransitionCancelCapture` | `TransitionEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onTransitionEnd` | `TransitionEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onTransitionEndCapture` | `TransitionEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onTransitionRun` | `TransitionEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onTransitionRunCapture` | `TransitionEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onTransitionStart` | `TransitionEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onTransitionStartCapture` | `TransitionEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onWheel` | `WheelEventHandler<HTMLSpanElement> | undefined` | — |  |
| `onWheelCapture` | `WheelEventHandler<HTMLSpanElement> | undefined` | — |  |
| `token` | `TokenSegment<PromptFieldTokenValue>` | — |  |
| `translate` | `"no" | "yes" | undefined` | — |  |

### PromptFieldToolbar

```tsx
<PromptFieldToolbar>
  <InsertMenuButton>
    <AttachFileMenuItem />
    <SubmenuTrigger>
      <InsertTextMenuItem /> or <InsertTokenMenuItem /> or <CommandMenuItem />
      <Menu />
    </SubmenuTrigger>
  </InsertMenuButton>
  <PromptFieldVoiceButton />
  <PromptFieldSubmitButton />
</PromptFieldToolbar>
```

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `children` | `ReactNode` | — |  |

#### InsertMenuButton

#### AttachFileMenuItem

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `aria-label` | `string | undefined` | — | An accessibility label for this item. |
| `id` | `Key | undefined` | — | The unique id of the item. |
| `isDisabled` | `boolean | undefined` | — | Whether the item is disabled. |
| `onAction` | `(() => void) | undefined` | — | Handler that is called when the item is selected. |
| `onBlur` | `((e: FocusEvent<Element>) => void) | undefined` | — | Handler that is called when the element loses focus. |
| `onFocus` | `((e: FocusEvent<Element>) => void) | undefined` | — | Handler that is called when the element receives focus. |
| `onFocusChange` | `((isFocused: boolean) => void) | undefined` | — | Handler that is called when the element's focus status changes. |
| `onHoverChange` | `((isHovering: boolean) => void) | undefined` | — | Handler that is called when the hover state changes. |
| `onHoverEnd` | `((e: HoverEvent) => void) | undefined` | — | Handler that is called when a hover interaction ends. |
| `onHoverStart` | `((e: HoverEvent) => void) | undefined` | — | Handler that is called when a hover interaction starts. |
| `onPress` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when the press is released over the target. |
| `onPressChange` | `((isPressed: boolean) => void) | undefined` | — | Handler that is called when the press state changes. |
| `onPressEnd` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when a press interaction ends, either over the target or when the pointer leaves the target. |
| `onPressStart` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when a press interaction starts. |
| `onPressUp` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when a press is released over the target, regardless of whether it started on the target or not. |
| `shouldCloseOnSelect` | `boolean | undefined` | — | Whether the menu should close when the menu item is selected. |
| `styles` | `StylesProp | undefined` | — | Spectrum-defined styles, returned by the `style()` macro. |
| `textValue` | `string | undefined` | — | A string representation of the item's contents, used for features like typeahead. |
| `value` | `object | undefined` | — | The object value that this item represents. When using dynamic collections, this is set automatically. |

#### InsertTextMenuItem

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `aria-label` | `string | undefined` | — | An accessibility label for this item. |
| `children` | `ReactNode` | — | The contents of the item. |
| `id` | `Key | undefined` | — | The unique id of the item. |
| `isDisabled` | `boolean | undefined` | — | Whether the item is disabled. |
| `onAction` | `(() => void) | undefined` | — | Handler that is called when the item is selected. |
| `onBlur` | `((e: FocusEvent<Element>) => void) | undefined` | — | Handler that is called when the element loses focus. |
| `onFocus` | `((e: FocusEvent<Element>) => void) | undefined` | — | Handler that is called when the element receives focus. |
| `onFocusChange` | `((isFocused: boolean) => void) | undefined` | — | Handler that is called when the element's focus status changes. |
| `onHoverChange` | `((isHovering: boolean) => void) | undefined` | — | Handler that is called when the hover state changes. |
| `onHoverEnd` | `((e: HoverEvent) => void) | undefined` | — | Handler that is called when a hover interaction ends. |
| `onHoverStart` | `((e: HoverEvent) => void) | undefined` | — | Handler that is called when a hover interaction starts. |
| `onPress` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when the press is released over the target. |
| `onPressChange` | `((isPressed: boolean) => void) | undefined` | — | Handler that is called when the press state changes. |
| `onPressEnd` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when a press interaction ends, either over the target or when the pointer leaves the target. |
| `onPressStart` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when a press interaction starts. |
| `onPressUp` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when a press is released over the target, regardless of whether it started on the target or not. |
| `shouldCloseOnSelect` | `boolean | undefined` | — | Whether the menu should close when the menu item is selected. |
| `styles` | `StylesProp | undefined` | — | Spectrum-defined styles, returned by the `style()` macro. |
| `text` | `string` | — |  |
| `textValue` | `string | undefined` | — | A string representation of the item's contents, used for features like typeahead. |

#### InsertTokenMenuItem

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `aria-label` | `string | undefined` | — | An accessibility label for this item. |
| `children` | `ReactNode` | — | The contents of the item. |
| `id` | `Key | undefined` | — | The unique id of the item. |
| `isDisabled` | `boolean | undefined` | — | Whether the item is disabled. |
| `onAction` | `(() => void) | undefined` | — | Handler that is called when the item is selected. |
| `onBlur` | `((e: FocusEvent<Element>) => void) | undefined` | — | Handler that is called when the element loses focus. |
| `onFocus` | `((e: FocusEvent<Element>) => void) | undefined` | — | Handler that is called when the element receives focus. |
| `onFocusChange` | `((isFocused: boolean) => void) | undefined` | — | Handler that is called when the element's focus status changes. |
| `onHoverChange` | `((isHovering: boolean) => void) | undefined` | — | Handler that is called when the hover state changes. |
| `onHoverEnd` | `((e: HoverEvent) => void) | undefined` | — | Handler that is called when a hover interaction ends. |
| `onHoverStart` | `((e: HoverEvent) => void) | undefined` | — | Handler that is called when a hover interaction starts. |
| `onPress` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when the press is released over the target. |
| `onPressChange` | `((isPressed: boolean) => void) | undefined` | — | Handler that is called when the press state changes. |
| `onPressEnd` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when a press interaction ends, either over the target or when the pointer leaves the target. |
| `onPressStart` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when a press interaction starts. |
| `onPressUp` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when a press is released over the target, regardless of whether it started on the target or not. |
| `shouldCloseOnSelect` | `boolean | undefined` | — | Whether the menu should close when the menu item is selected. |
| `styles` | `StylesProp | undefined` | — | Spectrum-defined styles, returned by the `style()` macro. |
| `textValue` | `string | undefined` | — | A string representation of the item's contents, used for features like typeahead. |
| `token` | `TokenSegment<PromptFieldTokenValue>` | — |  |

#### CommandMenuItem

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `aria-label` | `string | undefined` | — | An accessibility label for this item. |
| `children` | `ReactNode` | — | The contents of the item. |
| `id` | `Key | undefined` | — | The unique id of the item. |
| `isDisabled` | `boolean | undefined` | — | Whether the item is disabled. |
| `onAction` | `(() => void) | undefined` | — | Handler that is called when the item is selected. |
| `onBlur` | `((e: FocusEvent<Element>) => void) | undefined` | — | Handler that is called when the element loses focus. |
| `onFocus` | `((e: FocusEvent<Element>) => void) | undefined` | — | Handler that is called when the element receives focus. |
| `onFocusChange` | `((isFocused: boolean) => void) | undefined` | — | Handler that is called when the element's focus status changes. |
| `onHoverChange` | `((isHovering: boolean) => void) | undefined` | — | Handler that is called when the hover state changes. |
| `onHoverEnd` | `((e: HoverEvent) => void) | undefined` | — | Handler that is called when a hover interaction ends. |
| `onHoverStart` | `((e: HoverEvent) => void) | undefined` | — | Handler that is called when a hover interaction starts. |
| `onPress` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when the press is released over the target. |
| `onPressChange` | `((isPressed: boolean) => void) | undefined` | — | Handler that is called when the press state changes. |
| `onPressEnd` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when a press interaction ends, either over the target or when the pointer leaves the target. |
| `onPressStart` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when a press interaction starts. |
| `onPressUp` | `((e: PressEvent) => void) | undefined` | — | Handler that is called when a press is released over the target, regardless of whether it started on the target or not. |
| `shouldCloseOnSelect` | `boolean | undefined` | — | Whether the menu should close when the menu item is selected. |
| `styles` | `StylesProp | undefined` | — | Spectrum-defined styles, returned by the `style()` macro. |
| `textValue` | `string | undefined` | — | A string representation of the item's contents, used for features like typeahead. |
| `value` | `object | undefined` | — | The object value that this item represents. When using dynamic collections, this is set automatically. |

#### PromptFieldVoiceButton

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `isDisabled` | `boolean | undefined` | — |  |
| `lang` | `string | undefined` | — |  |
| `onError` | `((code: VoiceInputErrorCode) => void) | undefined` | — |  |
| `onToggle` | `((isListening: boolean) => void) | undefined` | — |  |

#### PromptFieldSubmitButton

## PixelLoader

| Name | Type | Default | Description |
|------|------|---------|-------------|
| `className` | `string | undefined` | — | A custom CSS class to apply. |
| `color` | `string | undefined` | 'currentColor' | The color of the icon. |
| `icon` | `Cell[] | Cell[][] | undefined` | — | The icon or sequence of icons to display. These should be imported from '@react-spectrum/ai/loader'. |
| `isPlaying` | `boolean | undefined` | — | Whether the animation is playing. |
| `size` | `number | undefined` | — | Size of the loader in pixels. Multiples of 7 render evenly on the pixel grid. |
