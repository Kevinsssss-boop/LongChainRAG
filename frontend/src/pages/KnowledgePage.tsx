import { useState } from 'react';
import { Upload, Button, Card, Typography, App, Space } from 'antd';
import { UploadOutlined, ReloadOutlined, InboxOutlined } from '@ant-design/icons';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { knowledgeAPI } from '../api/knowledge';
import { DocumentList } from '../components/Knowledge/DocumentList';
import { ChunkPreview } from '../components/Knowledge/ChunkPreview';

const { Title } = Typography;
const { Dragger } = Upload;

export function KnowledgePage() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [chunkModalOpen, setChunkModalOpen] = useState(false);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const { message } = App.useApp();
  const queryClient = useQueryClient();

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['documents', page, pageSize],
    queryFn: () => knowledgeAPI.list(page, pageSize),
  });

  const { data: chunksData, isFetching: chunksLoading } = useQuery({
    queryKey: ['chunks', selectedDocId],
    queryFn: () => knowledgeAPI.getChunks(selectedDocId!),
    enabled: !!selectedDocId && chunkModalOpen,
  });

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      await knowledgeAPI.upload(file);
      message.success(`${file.name} 上传成功`);
      refetch();
    } catch (err: any) {
      message.error(err.response?.data?.detail || '上传失败');
    } finally {
      setUploading(false);
    }
    return false; // prevent default upload
  };

  const handleViewChunks = (docId: string) => {
    setSelectedDocId(docId);
    setChunkModalOpen(true);
  };

  return (
    <div style={{ padding: 24, height: '100%', overflow: 'auto' }}>
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <Title level={4} style={{ margin: 0 }}>
            知识库管理
          </Title>
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
            刷新
          </Button>
        </div>

        <Card style={{ marginBottom: 24, borderRadius: 12 }}>
          <Dragger
            multiple
            accept=".pdf,.txt,.csv,.md"
            showUploadList={false}
            beforeUpload={handleUpload}
            disabled={uploading}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
            <p className="ant-upload-hint">支持 PDF、TXT、CSV、Markdown 格式，单个文件不超过 50MB</p>
          </Dragger>
        </Card>

        <Card title={`文档列表（共 ${data?.data.total || 0} 个）`} style={{ borderRadius: 12 }}>
          <DocumentList
            documents={data?.data.items || []}
            loading={isLoading}
            total={data?.data.total || 0}
            page={page}
            pageSize={pageSize}
            onPageChange={(p, ps) => {
              setPage(p);
              setPageSize(ps);
            }}
            onRefresh={() => refetch()}
            onViewChunks={handleViewChunks}
          />
        </Card>

        <ChunkPreview
          open={chunkModalOpen}
          chunks={chunksData?.data.chunks || []}
          loading={chunksLoading}
          onClose={() => {
            setChunkModalOpen(false);
            setSelectedDocId(null);
          }}
        />
      </div>
    </div>
  );
}