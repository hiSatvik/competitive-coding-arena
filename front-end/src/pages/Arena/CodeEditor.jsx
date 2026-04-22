import Editor from "@monaco-editor/react";

export default function CodeEditor({ code, setCode }) {
  const handleEditorChange = (value) => {
    setCode(value);
  };

  return (
    <div className="w-full h-full border-b border-white/10 bg-black/80">
      <Editor
        height="100%"
        theme="vs-dark"
        language="cpp"
        value={code}
        onChange={handleEditorChange}
        options={{
          minimap: { enabled: false },
          fontSize: 16,
          fontFamily: "'Fira Code', monospace",
          fontLigatures: true,
          padding: { top: 24 },
          scrollBeyondLastLine: false,
          smoothScrolling: true,
          cursorBlinking: "smooth",
        }}
        loading={<div className="text-pink-500 font-orbitron p-6">INITIALIZING WORKSPACE...</div>}
      />
    </div>
  );
}