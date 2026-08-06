import { Card, Typography, Tag, Space } from 'antd';
import { FileTextOutlined } from '@ant-design/icons';
import { Citation } from '../../api/session';

const { Text, Paragraph } = Typography;

interface CitationCardProps {
  citations: Citation[];
}

export function CitationCard({ citations }: CitationCardProps) {
  if (!citations || citations.length === 0) return null;

  return (
    <Card
      size="small"
      title={
        <Space>
          <FileTextOutlined />
          <span>参考来源</span>
        </Space>
      }
      style={{
        marginTop: 12,
        borderRadius: 8,
        background: 'var(--ant-color-bg-container, #fafafa)',
      }}
    >
      {citations.map((cite) => (
        <div
          key={cite.index}
          style={{
            marginBottom: 12,
            padding: '8px 12px',
            background: '#fff',
            borderRadius: 6,
            border: '1px solid #f0f0f0',
          }}
        >
          <div style={{ marginBottom: 4 }}>
            <Tag color="blue">[{cite.index}]</Tag>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {cite.source}
            </Text>
            <Tag style={{ marginLeft: 8 }} color={cite.score > 0.7 ? 'green' : 'orange'}>
              相关度: {(cite.score * 100).toFixed(0)}%
            </Tag>
          </div>
          <Paragraph
            ellipsis={{ rows: 3, expandable: true, symbol: '展开' }}
            style={{ margin: 0, fontSize: 13, color: '#666' }}
          >
            {cite.content}
          </Paragraph>
        </div>
      ))}
    </Card>
  );
}