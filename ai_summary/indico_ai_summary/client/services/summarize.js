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
    params: {prompt},
  });
  return resp.data;
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
