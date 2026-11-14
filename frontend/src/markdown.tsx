import type { ReactNode } from "react";

function stripFrontMatter(text: string): string {
  if (!text.startsWith("---\n")) {
    return text;
  }
  const end = text.indexOf("\n---\n", 4);
  if (end === -1) {
    return text;
  }
  return text.slice(end + 5).trim();
}

function inline(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const pattern = /\*\*([^*]+)\*\*|\*([^*]+)\*/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let index = 0;
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) {
      nodes.push(text.slice(last, match.index));
    }
    if (match[1] !== undefined) {
      nodes.push(<strong key={`${keyPrefix}-b-${index}`}>{match[1]}</strong>);
    } else {
      nodes.push(<em key={`${keyPrefix}-i-${index}`}>{match[2]}</em>);
    }
    last = match.index + match[0].length;
    index += 1;
  }
  if (last < text.length) {
    nodes.push(text.slice(last));
  }
  return nodes;
}

export function Markdown({ text }: { text: string }) {
  const lines = stripFrontMatter(text).split("\n");
  const blocks: ReactNode[] = [];
  let paragraph: string[] = [];
  let list: string[] = [];
  let key = 0;

  function flushParagraph() {
    if (paragraph.length === 0) {
      return;
    }
    const content = paragraph.join(" ");
    blocks.push(<p key={`p-${key}`}>{inline(content, `p-${key}`)}</p>);
    paragraph = [];
    key += 1;
  }

  function flushList() {
    if (list.length === 0) {
      return;
    }
    blocks.push(
      <ul key={`ul-${key}`}>
        {list.map((item, itemIndex) => (
          <li key={`${key}-${itemIndex}`}>{inline(item, `li-${key}-${itemIndex}`)}</li>
        ))}
      </ul>,
    );
    list = [];
    key += 1;
  }

  for (const line of lines) {
    const heading = /^(#{1,4}) +(.+)$/.exec(line);
    if (heading) {
      flushParagraph();
      flushList();
      const level = heading[1].length;
      const content = inline(heading[2], `h-${key}`);
      const tag = level <= 1 ? "h2" : level === 2 ? "h3" : "h4";
      const HeadingTag = tag;
      blocks.push(<HeadingTag key={`h-${key}`}>{content}</HeadingTag>);
      key += 1;
      continue;
    }
    if (line.startsWith("- ")) {
      flushParagraph();
      list.push(line.slice(2));
      continue;
    }
    if (!line.trim()) {
      flushParagraph();
      flushList();
      continue;
    }
    flushList();
    paragraph.push(line.trim());
  }
  flushParagraph();
  flushList();

  return <div className="markdown">{blocks}</div>;
}
