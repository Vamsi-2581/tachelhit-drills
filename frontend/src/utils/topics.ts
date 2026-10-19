// Subject catalogue (mirror of backend/topics.py): what a drill is ABOUT, independent of its source tag.
export const TOPIC_LABELS: Record<string, string> = {
  'verbs': 'Verbs i conjugació',
  'pronoms': 'Pronoms i possessius',
  'preposicions': 'Preposicions i partícules',
  'preguntes': 'Preguntes',
  'negacio': 'Negació',
  'numeros': 'Números i quantitat',
  'temps-dies': 'Temps: hores, dies, estacions',
  'salutacions': 'Salutacions i cortesia',
  'presentacions': 'Presentar-se',
  'familia': 'Família i persones',
  'casa': 'Casa i objectes',
  'menjar': 'Menjar i beguda',
  'cos-salut': 'Cos i salut',
  'roba-colors': 'Roba i colors',
  'animals': 'Animals',
  'natura': 'Natura, muntanya i camp',
  'meteorologia': 'El temps que fa',
  'viatge': 'Viatge, camí i direccions',
  'mercat': 'Mercat i compres',
  'feina': 'Feina i oficis',
  'emocions': 'Emocions i opinions',
  'religio': 'Religió i benediccions',
  'festa-musica': 'Festa, música i ball',
  'aprendre': 'Escola i aprendre la llengua',
  'alfabet': 'Alfabet i lletres',
  'proverbis': 'Dites i proverbis',
  'canco': 'Lletra de cançó',
  'conte': 'Conte i narració',
  'vocabulari': 'Vocabulari: una paraula',
};

export const parseTopics = (s?: string | null): string[] =>
  (s || '').split(',').map((x) => x.trim()).filter((x) => x && TOPIC_LABELS[x]);

export const topicLabel = (slug: string): string => TOPIC_LABELS[slug] || slug;

/** Text a search box should match for a drill's subjects: slugs and their Catalan labels. */
export const topicsSearchText = (s?: string | null): string =>
  parseTopics(s).map((t) => `${t} ${topicLabel(t)}`).join(' ').toLowerCase();

/** Does the drill match a free-text query against its subjects (slug or label, any word)? */
export const topicsMatch = (s: string | null | undefined, q: string): boolean => {
  const needle = q.trim().toLowerCase();
  if (!needle) return false;
  return parseTopics(s).some((t) => t === needle || topicLabel(t).toLowerCase().includes(needle) || t.includes(needle));
};
