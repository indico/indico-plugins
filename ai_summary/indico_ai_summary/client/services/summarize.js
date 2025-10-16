// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2025 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

import {indicoAxios} from 'indico/utils/axios';

// request LLM summary from plugin backend
export async function fetchSummary(eventId, prompt) {
  const resp = await indicoAxios.get(`/plugin/ai-summary/summarize-event/${eventId}`, {
    params: {prompt: prompt || ''},
  });
  return resp.data;
}

// Stream LLM summary via Server-Sent Events (SSE). Returns a controller with
// an `close()` method and hooks for `onChunk`, `onDone`, and `onError`.
export function streamSummary(eventId, prompt, {onChunk, onDone, onError} = {}) {

  const url = `/plugin/ai-summary/summarize-event/${eventId}?prompt=${encodeURIComponent(prompt || '')}`;

  const es = new EventSource(url);
  let receivedAny = false;
  let closed = false;

  es.onmessage = e => {
    if (!e?.data) {
      return;
    }
    if (e.data === '[DONE]') {
      if (onDone) onDone();
      es.close();
      closed = true;
      return;
    }
    try {
      const payload = JSON.parse(e.data);
      if (payload?.summary_html && onChunk) {
        onChunk(payload.summary_html);
        receivedAny = true;
      }
      if (payload?.error) {
        if (onError) onError(payload.error);
        es.close();
        closed = true;
      }
    } catch (err) {
      // Non-JSON payloads are ignored
    }
  };

  es.onerror = async () => {
    if (!closed) {
      es.close();
      closed = true;
    }
    // Fallback to our usual fetch if we never received any data
    if (!receivedAny) {
      try {
        const resp = await indicoAxios.get(`/plugin/ai-summary/summarize-event/${eventId}`, {
          params: {prompt: prompt || ''},
        });
        const data = resp.data || {};
        if (data.summary_html && onChunk) {
          onChunk(data.summary_html);
        }
        if (onDone) onDone();
      } catch (e) {
        if (onError) onError('Unable to retrieve summary.');
      }
      return;
    }
    // Otherwise, we were in the middle of streaming and lost connection
    if (onError) {
      onError('Connection lost while streaming summary.');
    }
  };

  return {
    close: () => es.close(),
  };
}

// fetch current event notes
export async function fetchEventNote(eventId) {
  const resp = await indicoAxios.get(`/event/${eventId}/api/note`);
  return resp.data;
}

// save summary + existing notes back into Indico
export async function saveSummaryToEvent(eventId, html, revisionId) {
  return indicoAxios.post(`/event/${eventId}/api/note`, {
    source: html,
    render_mode: 'html',
    revision_id: revisionId,
  });
}
