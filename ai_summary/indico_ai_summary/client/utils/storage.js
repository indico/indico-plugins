// This file is part of the Indico plugins.
// Copyright (C) 2002 - 2025 CERN
//
// The Indico plugins are free software; you can redistribute
// them and/or modify them under the terms of the MIT License;
// see the LICENSE file for more details.

// provides helper functions for interacting with browser localStorage.
// stores user-saved prompts and generated summaries locally.

const PROMPT_KEY = 'savedPrompts';
const SUMMARY_KEY = 'hfSummaryHtml';

// load saved prompts
export function getSavedPrompts() {
  return JSON.parse(localStorage.getItem(PROMPT_KEY)) || [];
}

// save a new prompt
export function savePrompt(prompt) {
  const prompts = getSavedPrompts();
  prompts.push(prompt);
  localStorage.setItem(PROMPT_KEY, JSON.stringify(prompts));
  return prompts;
}

// delete a saved prompt by index
export function deletePrompt(index) {
  const prompts = getSavedPrompts().filter((_, i) => i !== index);
  localStorage.setItem(PROMPT_KEY, JSON.stringify(prompts));
  return prompts;
}

// retrieve cached summary
export function getSummary() {
  return localStorage.getItem(SUMMARY_KEY) || '';
}

// save summary to localStorage
export function saveSummary(summary) {
  localStorage.setItem(SUMMARY_KEY, summary);
}

// clear cached summary
export function clearSummary() {
  localStorage.removeItem(SUMMARY_KEY);
}
