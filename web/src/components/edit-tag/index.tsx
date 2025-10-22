import { PlusOutlined } from '@ant-design/icons';
import { TweenOneGroup } from 'rc-tween-one';
import React, { useEffect, useRef, useState } from 'react';

import { X } from 'lucide-react';
import { Button } from '../ui/button';
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from '../ui/hover-card';
import { Input } from '../ui/input';
interface EditTagsProps {
  value?: string[];
  onChange?: (tags: string[]) => void;
}

const EditTag = React.forwardRef<HTMLDivElement, EditTagsProps>(
  ({ value = [], onChange }: EditTagsProps, ref) => {
    const [inputVisible, setInputVisible] = useState(false);
    const [inputValue, setInputValue] = useState('');
    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
      if (inputVisible) {
        inputRef.current?.focus();
      }
    }, [inputVisible]);

    const handleClose = (removedTag: string) => {
      console.log('🗑️ EditTag handleClose called, removing:', removedTag);
      console.log('🗑️ Current value:', value);
      const newTags = value?.filter((tag) => tag !== removedTag);
      console.log('🗑️ New tags:', newTags);
      console.log('🗑️ onChange function:', onChange);
      onChange?.(newTags ?? []);
    };

    const showInput = () => {
      setInputVisible(true);
    };

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      setInputValue(e.target.value);
    };

    const handleInputConfirm = () => {
      console.log('➕ EditTag handleInputConfirm called');
      console.log('➕ Input value:', inputValue);
      console.log('➕ Current tags:', value);
      if (inputValue) {
        const newTags = inputValue
          .split(';')
          .map((tag) => tag.trim())
          .filter((tag) => tag && !(value || []).includes(tag));
        console.log('➕ New tags to add:', newTags);
        console.log('➕ Final tags:', [...(value || []), ...newTags]);
        console.log('➕ onChange function:', onChange);
        onChange?.([...(value || []), ...newTags]);
      }
      setInputVisible(false);
      setInputValue('');
    };

    const forMap = (tag: string) => {
      return (
        <div
          key={tag}
          className="inline-flex items-center gap-1.5 border-dashed border px-2 py-1 rounded-sm bg-bg-card"
        >
          <HoverCard>
            <HoverCardContent side="top">{tag}</HoverCardContent>
            <HoverCardTrigger asChild>
              <span className="max-w-[200px] overflow-hidden text-ellipsis whitespace-nowrap cursor-default block">
                {tag}
              </span>
            </HoverCardTrigger>
          </HoverCard>
          <X
            className="w-4 h-4 text-muted-foreground hover:text-primary cursor-pointer flex-shrink-0"
            onClick={(e) => {
              console.log('🗑️ Delete button clicked for:', tag);
              e.preventDefault();
              e.stopPropagation();
              handleClose(tag);
            }}
          />
        </div>
      );
    };

    const tagChild = value?.map(forMap);

    const tagPlusStyle: React.CSSProperties = {
      borderStyle: 'dashed',
    };

    return (
      <div>
        {inputVisible ? (
          <Input
            ref={inputRef}
            type="text"
            className="h-8 bg-bg-card"
            value={inputValue}
            onChange={handleInputChange}
            onBlur={handleInputConfirm}
            onKeyDown={(e) => {
              if (e?.key === 'Enter') {
                handleInputConfirm();
              }
            }}
          />
        ) : (
          <Button
            variant="dashed"
            className="w-fit flex items-center justify-center gap-2 bg-bg-card"
            onClick={showInput}
            style={tagPlusStyle}
          >
            <PlusOutlined />
          </Button>
        )}
        {Array.isArray(tagChild) && tagChild.length > 0 && (
          <TweenOneGroup
            className="flex gap-2 flex-wrap mt-2"
            enter={{
              scale: 0.8,
              opacity: 0,
              type: 'from',
              duration: 100,
            }}
            onEnd={(e) => {
              if (e.type === 'appear' || e.type === 'enter') {
                (e.target as any).style = 'display: inline-block';
              }
            }}
            leave={{ opacity: 0, width: 0, scale: 0, duration: 200 }}
            appear={false}
          >
            {tagChild}
          </TweenOneGroup>
        )}
      </div>
    );
  },
);

export default EditTag;
