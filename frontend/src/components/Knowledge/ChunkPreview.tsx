import { Modal, List, Typography, Tag } from 'antd';

const { Text, Paragraph } = Typography;

interface ChunkPreviewProps {
  open: boolean;
  chunks: { chunk_index: number; content: string; metadata: any }[];
  loading: boolean;
  onClose: () => void;
}

export function ChunkPreview({ open, chunks, loading, onClose }: ChunkPreviewProps) {
  return (
    <Modal
      title={`文档分块预览（共 ${chunks.length} 块）`}
      open={open}
      onCancel={onClose}
      footer={null}
      width={800}
    >
      <List
        dataSource={chunks}
        loading={loading}
        renderItem={(chunk) => (
          <List.Item
            style={{
              display: 'block',
              padding: '12px 0',
              borderBottom: '1px solid #f0f0f0',
            }}
          >
            <div style={{ marginBottom: 6 }}>
              <Tag color="blue">块 #{chunk.chunk_index + 1}</Tag>
              {chunk.metadata?.source && (
                <Tag color="purple">{chunk.metadata.source}</Tag>
              )}
              {chunk.metadata?.page !== undefined && (
                <Tag>第 {chunk.metadata.page + 1} 页</Tag>
              )}
            </div>
            <Paragraph
              ellipsis={{ rows: 5, expandable: true, symbol: '展开全文' }}
              style={{ color: '#666', fontSize: 13 }}
            >
              {chunk.content}
            </Paragraph>
          </List.Item>
        )}
      />
    </Modal>
  );
}