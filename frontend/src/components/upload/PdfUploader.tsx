import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, Loader2, AlertCircle, Link2, Plus, X } from 'lucide-react';
import { uploadDegreePdf, uploadDegreeUrls } from '../../services/api';

type UploadMode = 'pdf' | 'url';

interface PdfUploaderProps {
  onUploadComplete: (sessionId: string) => void;
  onUrlUploadComplete: (sessionId: string) => void;
  onUseSample: () => void;
}

export default function PdfUploader({ onUploadComplete, onUrlUploadComplete, onUseSample }: PdfUploaderProps) {
  const [mode, setMode] = useState<UploadMode>('pdf');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  // URL mode state
  const [urls, setUrls] = useState<string[]>(['']);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      const file = acceptedFiles[0];
      if (!file) return;

      setFileName(file.name);
      setUploading(true);
      setError(null);

      try {
        const { session_id } = await uploadDegreePdf(file);
        onUploadComplete(session_id);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Upload failed');
      } finally {
        setUploading(false);
      }
    },
    [onUploadComplete],
  );

  const handleUrlSubmit = useCallback(async () => {
    const validUrls = urls.map(u => u.trim()).filter(Boolean);
    if (validUrls.length === 0) {
      setError('Enter at least one URL');
      return;
    }
    // Basic URL validation
    for (const url of validUrls) {
      try { new URL(url); } catch {
        setError(`Invalid URL: ${url}`);
        return;
      }
    }

    setUploading(true);
    setError(null);
    try {
      const { session_id } = await uploadDegreeUrls(validUrls);
      onUrlUploadComplete(session_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'URL extraction failed');
    } finally {
      setUploading(false);
    }
  }, [urls, onUrlUploadComplete]);

  const addUrlField = () => {
    if (urls.length < 5) setUrls([...urls, '']);
  };

  const removeUrlField = (index: number) => {
    if (urls.length > 1) setUrls(urls.filter((_, i) => i !== index));
  };

  const updateUrl = (index: number, value: string) => {
    setUrls(urls.map((u, i) => (i === index ? value : u)));
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/webp': ['.webp'],
      'video/mp4': ['.mp4'],
      'video/webm': ['.webm'],
    },
    maxFiles: 1,
    disabled: uploading,
  });

  return (
    <div className="space-y-4">
      {/* Mode Toggle */}
      <div className="flex bg-slate-100 rounded-lg p-1 gap-1" role="tablist" aria-label="Upload method">
        <button
          role="tab"
          aria-selected={mode === 'pdf'}
          aria-controls="upload-panel-pdf"
          onClick={() => { setMode('pdf'); setError(null); }}
          className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-md text-sm font-medium transition-all
            ${mode === 'pdf' ? 'bg-white text-violet-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
        >
          <FileText className="w-4 h-4" />
          Upload PDF
        </button>
        <button
          role="tab"
          aria-selected={mode === 'url'}
          aria-controls="upload-panel-url"
          onClick={() => { setMode('url'); setError(null); }}
          className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-md text-sm font-medium transition-all
            ${mode === 'url' ? 'bg-white text-violet-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
        >
          <Link2 className="w-4 h-4" />
          Paste URLs
        </button>
      </div>

      {/* PDF Drop Zone */}
      {mode === 'pdf' && (
        <div
          {...getRootProps()}
          className={`bg-white rounded-xl border-2 border-dashed p-12 text-center transition-all cursor-pointer
            ${isDragActive ? 'border-violet-500 bg-violet-50 scale-[1.01]' : 'border-slate-300 hover:border-violet-400 hover:bg-violet-50/30'}
            ${uploading ? 'opacity-60 cursor-wait' : ''}
          `}
        >
          <input {...getInputProps()} />
          <div className="flex flex-col items-center gap-3">
            {uploading ? (
              <Loader2 className="w-10 h-10 text-violet-500 animate-spin" />
            ) : isDragActive ? (
              <Upload className="w-10 h-10 text-violet-500" />
            ) : (
              <FileText className="w-10 h-10 text-slate-400" />
            )}

            {uploading ? (
              <p className="text-violet-600 font-medium">Uploading {fileName}...</p>
            ) : isDragActive ? (
              <p className="text-violet-600 font-medium">Drop your file here</p>
            ) : (
              <>
                <p className="text-slate-700 font-medium">
                  Drag & drop your degree requirements
                </p>
                <p className="text-sm text-slate-400">PDF, image, or screen recording — or click to browse</p>
              </>
            )}
          </div>
        </div>
      )}

      {/* URL Input */}
      {mode === 'url' && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-3">
          <p className="text-sm text-slate-500">
            Paste links to your university's degree requirements pages (up to 5).
          </p>
          {urls.map((url, i) => (
            <div key={i} className="flex items-center gap-2">
              <input
                type="url"
                value={url}
                onChange={(e) => updateUrl(i, e.target.value)}
                placeholder={`https://catalog.university.edu/cs-requirements${i > 0 ? `-page-${i + 1}` : ''}`}
                disabled={uploading}
                className="flex-1 px-3 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent disabled:opacity-50"
              />
              {urls.length > 1 && (
                <button
                  onClick={() => removeUrlField(i)}
                  disabled={uploading}
                  className="p-1.5 text-slate-400 hover:text-red-500 transition-colors disabled:opacity-50"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          ))}
          <div className="flex items-center justify-between">
            {urls.length < 5 && (
              <button
                onClick={addUrlField}
                disabled={uploading}
                className="flex items-center gap-1 text-sm text-violet-600 hover:text-violet-800 disabled:opacity-50"
              >
                <Plus className="w-3.5 h-3.5" />
                Add another URL
              </button>
            )}
            <button
              onClick={handleUrlSubmit}
              disabled={uploading || urls.every(u => !u.trim())}
              className="ml-auto flex items-center gap-2 px-5 py-2 bg-violet-600 text-white text-sm font-medium rounded-lg hover:bg-violet-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {uploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Extracting...
                </>
              ) : (
                <>
                  <Link2 className="w-4 h-4" />
                  Extract & Parse
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 rounded-lg px-4 py-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="text-center">
        <span className="text-sm text-slate-400">or </span>
        <button
          onClick={onUseSample}
          className="text-sm text-violet-600 hover:text-violet-800 underline underline-offset-2"
        >
          use sample CS degree data
        </button>
      </div>
    </div>
  );
}
