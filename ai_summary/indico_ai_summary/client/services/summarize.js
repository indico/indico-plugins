// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2025 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import summarizeEventURL from 'indico-url:plugin_ai_summary.summarize_event';
import eventNoteURL from 'indico-url:event_notes.api';


import {indicoAxios} from 'indico/utils/axios';

// request LLM summary from plugin backend
export async function fetchSummary(eventId, prompt) {
  const resp = await indicoAxios.post(summarizeEventURL({event_id: eventId}), {
    prompt: prompt || '',
  });
  return resp.data;
}

// Parse a single SSE data line and return the payload
function parseSSELine(line) {
  if (!line.startsWith('data: ')) {
    return null;
  }

  const data = line.slice(6); // Remove 'data: ' prefix

  if (data === '[DONE]') {
    return {done: true};
  }

  try {
    return {done: false, payload: JSON.parse(data)};
  } catch (err) {
    // Non-JSON payloads are ignored
    return null;
  }
}

// Process the stream and call callbacks for each chunk
async function processStreamResponse(response, callbacks, state) {
  const {onChunk, onDone, onError} = callbacks;
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (!state.closed) {
    const {done, value} = await reader.read();

    if (done) {
      break;
    }

    // Decode the chunk and add to buffer
    buffer += decoder.decode(value, {stream: true});

    // Process complete lines
    const lines = buffer.split('\n');
    // Keep the last (potentially incomplete) line in the buffer
    buffer = lines.pop() || '';

    for (const line of lines) {
      // Check if stream was aborted during processing
      if (state.closed) {
        return;
      }

      const result = parseSSELine(line);

      if (!result) {
        continue;
      }

      if (result.done) {
        if (onDone) onDone();
        state.closed = true;
        return;
      }

      const {payload} = result;
      if (payload?.summary_html && onChunk) {
        onChunk(payload.summary_html);
        state.receivedAny = true;
      }
      if (payload?.error) {
        if (onError) onError(payload.error);
        state.closed = true;
        return;
      }
    }
  }

  // Only call onDone if not manually closed
  if (!state.closed && onDone) {
    onDone();
  }
}

// Fallback to non-streaming request
async function fallbackToRegularRequest(eventId, prompt, callbacks) {
  const {onChunk, onDone, onError} = callbacks;
  try {
    const resp = await indicoAxios.post(summarizeEventURL({event_id: eventId}), {
      prompt: prompt || '',
    });
    const data = resp.data || {};
    if (data.summary_html && onChunk) {
      onChunk(data.summary_html);
    }
    if (onDone) onDone();
  } catch (e) {
    if (onError) onError('Unable to retrieve summary.');
  }
}

// Stream LLM summary via fetch.
// Returns a controller with an `abort()` method and hooks for `onChunk`, `onDone`, and `onError`.
export function streamSummary(eventId, prompt, {onChunk, onDone, onError} = {}) {
  const abortController = new AbortController();
  const state = {closed: false, receivedAny: false};
  const callbacks = {onChunk, onDone, onError};

  const processStream = async () => {
    try {
      // Normally, we would use IndicoAxios here with `responseType: 'stream'`, but this causes
      // the output to be not as smooth.
      const response = await fetch(summarizeEventURL({event_id: eventId}), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': document.getElementById('csrf-token').getAttribute('content'),
        },
        body: JSON.stringify({prompt: prompt || ''}),
        signal: abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      await processStreamResponse(response, callbacks, state);
    } catch (err) {
      // If manually aborted via abort(), onDone is already called there
      if (state.closed) {
        return;
      }

      // Handle AbortError from fetch
      if (err.name === 'AbortError') {
        if (onDone) onDone();
        return;
      }

      // Fallback to regular POST if streaming failed and we haven't received any data
      if (!state.receivedAny) {
        await fallbackToRegularRequest(eventId, prompt, callbacks);
        return;
      }

      // Otherwise, we were in the middle of streaming and lost connection
      if (onError) {
        onError('Connection lost whilst streaming summary.');
      }
    }
  };

  // Start processing asynchronously (fire and forget)
  void processStream();

  return {
    abort: () => {
      if (state.closed) {
        return; // Already closed
      }
      state.closed = true;

      // Abort the fetch request - this will cause the reader to error
      abortController.abort();

      // Call onDone immediately to update UI
      if (onDone) {
        onDone();
      }
    },
  };
}

// fetch current event notes
export async function fetchEventNote(eventId) {
  const resp = await indicoAxios.get(eventNoteURL({event_id: eventId}));
  return resp.data;
}

// save summary + existing notes back into Indico
export async function saveSummaryToEvent(eventId, html, revisionId) {
  return indicoAxios.post(eventNoteURL({event_id: eventId}), {
    source: html,
    render_mode: 'html',
    revision_id: revisionId,
  });
}
