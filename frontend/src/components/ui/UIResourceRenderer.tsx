/**
 * UIResourceRenderer - Renders MCP-UI resources as sandboxed iframes.
 *
 * This component takes UI resource data from agent responses and renders
 * them as secure, sandboxed HTML widgets in the chat interface.
 */

import { useMemo } from 'react';

export interface UIResource {
  uri: string;
  mimeType: string;
  text: string; // HTML content
}

interface UIResourceRendererProps {
  resource: UIResource;
  className?: string;
}

export const UIResourceRenderer = ({ resource, className = '' }: UIResourceRendererProps) => {
  // Create a blob URL for the HTML content
  const iframeSrc = useMemo(() => {
    if (resource.mimeType !== 'text/html') {
      return null;
    }

    const blob = new Blob([resource.text], { type: 'text/html' });
    return URL.createObjectURL(blob);
  }, [resource.text, resource.mimeType]);

  // Determine height based on widget type
  const getHeightFromUri = (uri: string): string => {
    if (uri.includes('calendly')) return '1100px'; // Full Calendly widget without scrolling
    if (uri.includes('github')) return '520px'; // GitHub profile with repos
    return '400px';
  };

  if (!iframeSrc) {
    return null;
  }

  return (
    <div className={`ui-resource-container my-2 sm:my-4 ${className}`}>
      <iframe
        src={iframeSrc}
        className="w-full rounded-lg border border-gray-700"
        style={{
          height: getHeightFromUri(resource.uri),
          background: 'transparent'
        }}
        sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
        title={`Widget: ${resource.uri}`}
      />
    </div>
  );
};

/**
 * Utility function to extract UI resources from agent response text.
 * Looks for __UI_RESOURCE__...json...__END_UI_RESOURCE__ markers.
 */
export function extractUIResources(content: string): {
  cleanContent: string;
  resources: UIResource[]
} {
  const resourcePattern = /__UI_RESOURCE__(\{.*?\})__END_UI_RESOURCE__/gs;
  const resources: UIResource[] = [];

  // Extract all UI resources
  let match;
  while ((match = resourcePattern.exec(content)) !== null) {
    try {
      const resourceData = JSON.parse(match[1]);
      resources.push({
        uri: resourceData.uri,
        mimeType: resourceData.mimeType,
        text: resourceData.text
      });
    } catch (e) {
      console.error('Failed to parse UI resource:', e);
    }
  }

  // Remove the resource markers from the content
  const cleanContent = content
    .replace(/__UI_RESOURCE__\{.*?\}__END_UI_RESOURCE__/gs, '')
    .trim();

  return { cleanContent, resources };
}

export default UIResourceRenderer;
