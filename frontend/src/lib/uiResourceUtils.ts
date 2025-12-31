/**
 * Utility functions for handling UI resources in messages
 */

interface UIResource {
  uri: string;
  mimeType: string;
  text: string;
}

/**
 * Creates resource markers from UI resources that can be prepended to message content
 * @param uiResources - Array of UI resource objects
 * @returns String containing all resource markers joined together
 */
export function createResourceMarkers(uiResources: UIResource[]): string {
  return (uiResources ?? [])
    .map(r => `__UI_RESOURCE__${JSON.stringify(r)}__END_UI_RESOURCE__`)
    .join('');
}

/**
 * Prepends UI resource markers to message content
 * @param content - The message content
 * @param uiResources - Array of UI resource objects
 * @returns Content with resource markers prepended (if any resources exist), otherwise original content
 */
export function prependResourceMarkers(content: string, uiResources: UIResource[]): string {
  const resourceMarkers = createResourceMarkers(uiResources);
  return resourceMarkers ? `${resourceMarkers}\n\n${content}` : content;
}
